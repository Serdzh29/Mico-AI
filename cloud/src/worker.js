// Mico Cloud: шлюз между программой Mico AI и Cloudflare Workers AI.
// В программе нет ключа: она получает от шлюза личный токен установки, а шлюз сам обращается к ИИ, выбирает модель и ведёт лимиты.
// Уровни: Lite (простые и дешёвые модели), Plus (сильные), Max (самые мощные и дорогие). Режим Auto сам выбирает уровень по вопросу.
// Лимиты считаются в «нейронах» Cloudflare: шлюз знает цену каждой модели и показывает программе, на сколько запросов хватит остатка.

const enc = new TextEncoder();
const today = () => new Date().toISOString().slice(0, 10);       // сутки по UTC: как у бесплатного лимита Cloudflare

const num = (v, d) => { const n = Number(v); return Number.isFinite(n) && n > 0 ? n : d; };
const json = (obj, status = 200, headers = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...headers } });

async function hmacHex(secret, msg) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(msg));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}
function safeEqual(a, b) {                                         // сравнение без утечки по времени
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

// ---------- счётчик: одна запись на ключ ("install:…", "global", "ip:…"), сбрасывается каждые сутки ----------
export class Meter {
  constructor(ctx) { this.ctx = ctx; }
  async fetch(request) {
    const { op, cost = 1, limit = 1 } = await request.json();
    const day = today();
    let st = (await this.ctx.storage.get("s")) || { d: day, n: 0 };
    if (st.d !== day) st = { d: day, n: 0 };
    if (op === "peek") return json({ ok: true, n: st.n, limit });
    if (op === "refund") {
      st.n = Math.max(0, st.n - cost);
      await this.ctx.storage.put("s", st);
      return json({ ok: true, n: st.n, limit });
    }
    if (st.n + cost > limit) return json({ ok: false, n: st.n, limit });
    st.n += cost;
    await this.ctx.storage.put("s", st);
    return json({ ok: true, n: st.n, limit });
  }
}
async function meter(env, name, op, cost, limit) {
  const stub = env.METER.get(env.METER.idFromName(name));
  const r = await stub.fetch("https://meter/x", { method: "POST", body: JSON.stringify({ op, cost, limit }) });
  return r.json();
}

// ---------- каталог моделей ----------
// Отобраны самые сильные и надёжные модели Cloudflare Workers AI, по уровням: Lite (быстро и дёшево), Plus (сильные), Max (самые мощные).
// Цены (нейронов за миллион токенов: на входе, на выходе) взяты со страницы цен Cloudflare Workers AI.
// alt: true: модель семейства gpt-oss, которой при сбое запроса «messages» пробуем формат «input» (Responses API).
// ext: внешний источник (groq, gemini, nvidia). Работает только если на воркере задан его секрет (см. EXT ниже); без секрета модель пропускается.
const M = {
  // Lite: простые вопросы, быстро и дёшево
  l31_8b: { id: "@cf/meta/llama-3.1-8b-instruct-fp8-fast", name: "Llama 3.1 8B", tier: "lite", pin: 4119, pout: 34868 },
  gm4: { id: "@cf/google/gemma-4-26b-a4b-it", name: "Gemma 4 26B", tier: "lite", pin: 9091, pout: 27273 },
  q3_30b: { id: "@cf/qwen/qwen3-30b-a3b-fp8", name: "Qwen3 30B-A3B", tier: "lite", pin: 4625, pout: 30475 },
  glm47f: { id: "@cf/zai-org/glm-4.7-flash", name: "GLM 4.7 Flash", tier: "lite", pin: 5500, pout: 36400 },
  l32_3b: { id: "@cf/meta/llama-3.2-3b-instruct", name: "Llama 3.2 3B", tier: "lite", pin: 4625, pout: 30475 },
  // Plus: сильные модели для сложных вопросов, текстов, кода и рассуждений
  l33: { id: "@cf/meta/llama-3.3-70b-instruct-fp8-fast", name: "Llama 3.3 70B", tier: "plus", pin: 26668, pout: 204805 },
  oss120: { id: "@cf/openai/gpt-oss-120b", name: "gpt-oss 120B", tier: "plus", pin: 31818, pout: 68182, alt: true },
  gm3: { id: "@cf/google/gemma-3-12b-it", name: "Gemma 3 12B", tier: "plus", pin: 31371, pout: 50560 },
  coder: { id: "@cf/qwen/qwen2.5-coder-32b-instruct", name: "Qwen2.5 Coder 32B", tier: "plus", pin: 60000, pout: 90909 },
  qwq: { id: "@cf/qwen/qwq-32b", name: "QwQ 32B", tier: "plus", pin: 60000, pout: 90909 },
  sc4: { id: "@cf/meta/llama-4-scout-17b-16e-instruct", name: "Llama 4 Scout 17B", tier: "plus", pin: 24545, pout: 77273 },
  dsf41: { id: "@cf/deepseek-ai/deepseek-v4.1-flash-1017", name: "DeepSeek V4.1 Flash", tier: "plus", pin: 27273, pout: 109091 },
  // Max: самые мощные и энергозатратные
  k26: { id: "@cf/moonshotai/kimi-k2.6", name: "Kimi K2.6", tier: "max", pin: 86364, pout: 363636 },
  dsp: { id: "@cf/deepseek-ai/deepseek-v4-pro-0813", name: "DeepSeek V4 Pro", tier: "max", pin: 120000, pout: 360000 },
  glm53: { id: "@cf/zai-org/glm-5.3", name: "GLM 5.3", tier: "max", pin: 127273, pout: 400000 },
  k27c: { id: "@cf/moonshotai/kimi-k2.7-code", name: "Kimi K2.7 Code", tier: "max", pin: 86364, pout: 363636 },
  // Внешние источники: бесплатные тарифы провайдеров. Идентификаторы моделей у провайдеров меняются: сверяйте со списками моделей на их сайтах.
  gq_8b: { ext: "groq", id: "llama-3.1-8b-instant", name: "Groq Llama 3.1 8B", tier: "lite" },
  gq_70b: { ext: "groq", id: "llama-3.3-70b-versatile", name: "Groq Llama 3.3 70B", tier: "plus" },
  gq_oss: { ext: "groq", id: "openai/gpt-oss-120b", name: "Groq gpt-oss 120B", tier: "plus" },
  gq_kimi: { ext: "groq", id: "moonshotai/kimi-k2-instruct-0905", name: "Groq Kimi K2", tier: "max" },
  gem_lite: { ext: "gemini", id: "gemini-2.5-flash-lite", name: "Gemini 2.5 Flash-Lite", tier: "lite" },
  gem_flash: { ext: "gemini", id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", tier: "plus" },
  gem_pro: { ext: "gemini", id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", tier: "max" },
  nv_8b: { ext: "nvidia", id: "meta/llama-3.1-8b-instruct", name: "NVIDIA Llama 3.1 8B", tier: "lite" },
  nv_70b: { ext: "nvidia", id: "meta/llama-3.3-70b-instruct", name: "NVIDIA Llama 3.3 70B", tier: "plus" },
  nv_405b: { ext: "nvidia", id: "meta/llama-3.1-405b-instruct", name: "NVIDIA Llama 3.1 405B", tier: "max" },
  nv_nemo: { ext: "nvidia", id: "nvidia/llama-3.1-nemotron-ultra-253b-v1", name: "NVIDIA Nemotron Ultra 253B", tier: "max" },
};
// Провайдеры с OpenAI-совместимым API. secret: имя секрета воркера (npx wrangler secret put …). Нет секрета: провайдер не используется.
const EXT = {
  groq: { secret: "GROQ_API_KEY", url: "https://api.groq.com/openai/v1/chat/completions" },
  gemini: { secret: "GEMINI_API_KEY", url: "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" },
  nvidia: { secret: "NVIDIA_API_KEY", url: "https://integrate.api.nvidia.com/v1/chat/completions" },
};
const extReady = (env, m) => !m.ext || !!(EXT[m.ext] && env[EXT[m.ext].secret]);
// Для каждого уровня и вида вопроса: кандидаты по порядку. Первый подходящий по цене берётся, при сбое пробуется следующий.
const CHAINS = {
  lite: {
    general: ["gq_8b", "l31_8b", "gem_lite", "nv_8b", "glm47f", "gm4", "l32_3b"], text: ["gem_lite", "gm4", "gq_8b", "l31_8b", "nv_8b", "glm47f"],
    code: ["gq_8b", "q3_30b", "gem_lite", "glm47f", "l31_8b", "nv_8b"], reason: ["gem_lite", "q3_30b", "gq_8b", "glm47f", "l31_8b"],
  },
  plus: {
    general: ["gq_70b", "l33", "gem_flash", "nv_70b", "oss120", "sc4", "dsf41"], text: ["gem_flash", "gm3", "gq_70b", "sc4", "nv_70b", "l33"],
    code: ["gq_70b", "coder", "gem_flash", "dsf41", "nv_70b", "l33", "oss120"], reason: ["gq_oss", "gem_flash", "oss120", "qwq", "l33"],
  },
  max: {
    general: ["gem_pro", "k26", "nv_nemo", "gq_kimi", "dsp", "glm53"], text: ["gem_pro", "glm53", "k26", "nv_405b", "dsp"],
    code: ["gq_kimi", "k27c", "gem_pro", "dsp", "k26", "nv_nemo"], reason: ["gem_pro", "nv_nemo", "dsp", "k26", "glm53"],
  },
};
const CHEAP = ["l32_3b"];                                           // запасной выход, когда доли почти не осталось
const TIERS = ["lite", "plus", "max"];
// Старые названия режимов (прошлые версии программы: быстро/умнее, потом Basic/Pro/Ultra) переезжают на новые уровни.
const LEGACY = { fast: "lite", smart: "plus", text: "plus", code: "plus", basic: "lite", pro: "plus", ultra: "max" };
const TYPICAL_IN = 1500, TYPICAL_OUT = 300;                         // «обычный» запрос для показа остатка в запросах

const cost = (m, inTok, outTok) => m.ext ? 0 : Math.max(1, Math.ceil(inTok * m.pin / 1e6 + outTok * m.pout / 1e6));

// ---------- вид вопроса и уровень для режима «Авто» ----------
const CODE_HINT = /(?<![а-яёa-z])код(?![а-яёa-z])|скрипт|функци[юяи]|python|питон|javascript|typescript|\bsql\b|\bhtml\b|\bcss\b|c\+\+|алгоритм|регулярк|regex|отладь|(?<![а-яё])баг(?![а-яё])|```|\bdef \b|\bclass \b|function |=>|#include/i;
const TEXT_HINT = /напиши (стих|песню|рассказ|письмо|пост|статью|сказку|поздравление|текст|описание)|сочини|перепиши|исправь текст|переведи|перевод|придумай (название|слоган|историю|сюжет)|translate|rewrite|poem|story|proofread/i;
const REASON_HINT = /реши|задач[ауи]|докажи|логик|математик|уравнени|вероятност|интеграл|производн|головоломк|сколько будет|посчитай|вычисли|prove|solve|puzzle|riddle|calculate/i;
const SMART_HINT = /объясни|сравни|почему|как работает|проанализ|разбер|распиши|план |стратег|explain|compare|why |how does|analy[sz]e|step by step|подробно|в чём разница|плюсы и минусы/i;
const ULTRA_HINT = /докажи|строго|олимпиад|архитектур|разработай (стратегию|систему|архитектуру)|напиши (программу|приложение|игру)|подробный (анализ|разбор)|исследуй|глубоко|во всех деталях|by contradiction|rigorous|in depth/i;

function lastUser(messages) {
  const m = [...messages].reverse().find(x => x.role === "user");
  return m ? m.content : "";
}
function detect(text) {
  if (CODE_HINT.test(text)) return "code";
  if (REASON_HINT.test(text) && !/^\s*сколько будет\s+[\d\s×x*+/\-().,]+\??\s*$/i.test(text)) return "reason";
  if (TEXT_HINT.test(text)) return "text";
  return "general";
}
function autoTier(text, kind) {
  if (ULTRA_HINT.test(text) || text.length > 1400) return "max";
  if (kind === "reason" && text.length <= 70) return "lite";            // короткий счёт не требует сильной модели
  if (kind === "code" || kind === "reason" || SMART_HINT.test(text) || text.length > 280) return "plus";
  if (kind === "text" && text.length > 160) return "plus";
  return "lite";
}
const estTokens = messages => Math.ceil(messages.reduce((n, m) => n + m.content.length, 0) / 2.8);

function cleanMessages(raw) {
  if (!Array.isArray(raw)) return null;
  const out = [];
  let total = 0;
  for (const m of raw.slice(-14)) {
    if (!m || typeof m.content !== "string") continue;
    const role = m.role === "assistant" || m.role === "system" ? m.role : "user";
    const content = m.content.slice(0, 6000);
    total += content.length;
    out.push({ role, content });
  }
  if (!out.length || total > 24000) return null;
  return out;
}

async function verifyToken(env, header) {
  const m = /^Bearer ([0-9a-f]{32})\.([0-9a-f]{64})$/.exec(header || "");
  if (!m) return null;
  const expect = await hmacHex(env.MICO_SECRET, "id:" + m[1]);
  return safeEqual(expect, m[2]) ? m[1] : null;
}

// ---------- остаток: доля этой установки и общая дневная доля аккаунта ----------
const limits = env => ({ install: num(env.INSTALL_NEURONS_DAY, 1000), global: num(env.GLOBAL_NEURONS_DAY, 9000) });
// Внешние источники считаются в запросах, отдельно от нейронов Cloudflare: доля установки и общая доля в сутки.
const extLimits = env => ({ install: num(env.EXT_INSTALL_DAY, 300), global: num(env.EXT_GLOBAL_DAY, 5000) });
async function extStanding(env, id) {
  const L = extLimits(env);
  const [i, g] = await Promise.all([meter(env, "ext-install:" + id, "peek", 0, L.install), meter(env, "ext-global", "peek", 0, L.global)]);
  return Math.min(Math.max(0, L.install - i.n), Math.max(0, L.global - g.n));
}
async function standing(env, id) {
  const L = limits(env);
  const [i, g] = await Promise.all([meter(env, "install:" + id, "peek", 0, L.install), meter(env, "global", "peek", 0, L.global)]);
  const installLeft = Math.max(0, L.install - i.n), globalLeft = Math.max(0, L.global - g.n);
  return { installLeft, globalLeft, left: Math.min(installLeft, globalLeft), installLimit: L.install, globalLimit: L.global };
}
const quotaHeaders = q => ({
  "x-mico-left": String(q.left), "x-mico-install-left": String(q.installLeft), "x-mico-global-left": String(q.globalLeft),
  "x-mico-install-limit": String(q.installLimit),
});
function tierSummary() {
  const out = {};
  for (const t of TIERS) {
    const m = M[CHAINS[t].general.find(k => !M[k].ext)];
    out[t] = { cost: cost(m, TYPICAL_IN, TYPICAL_OUT), model: m.name };
  }
  return out;
}

async function handleRegister(request, env) {
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const ipKey = "ip:" + (await hmacHex(env.MICO_SECRET, "ip:" + ip)).slice(0, 24);
  const r = await meter(env, ipKey, "take", 1, num(env.REGISTER_PER_IP_DAY, 10));
  if (!r.ok) return json({ error: "limit", scope: "register", message: "С этого адреса сегодня уже много новых установок." }, 429);
  const id = crypto.randomUUID().replaceAll("-", "");
  const sig = await hmacHex(env.MICO_SECRET, "id:" + id);
  return json({ token: `${id}.${sig}`, install_neurons_day: limits(env).install });
}

async function handleQuota(request, env) {
  const id = await verifyToken(env, request.headers.get("Authorization"));
  if (!id) return json({ error: "token", message: "Токен установки не подошёл." }, 401);
  const q = await standing(env, id);
  const models = Object.entries(M).filter(([, m]) => extReady(env, m)).map(([key, m]) => ({ key, name: m.name, tier: m.tier, cost: cost(m, TYPICAL_IN, TYPICAL_OUT) }));
  return json({ left: q.left, install_left: q.installLeft, global_left: q.globalLeft, install_limit: q.installLimit, global_limit: q.globalLimit,
                typical: { in: TYPICAL_IN, out: TYPICAL_OUT }, tiers: tierSummary(), models, resets: "00:00 UTC" });
}

// ---------- вызов модели ----------
function textOf(res) {
  if (typeof res === "string") return res;
  if (!res) return "";
  const pick = res.response ?? res.result?.response ?? res.choices?.[0]?.message?.content ?? res.output_text;
  if (typeof pick === "string") return pick;
  if (Array.isArray(res.output)) {
    return res.output.map(o => (Array.isArray(o.content) ? o.content.map(c => c.text || "").join("") : "")).join("");
  }
  return "";
}
const stripThink = s => String(s).replace(/<think>[\s\S]*?<\/think>/g, "").trim();

async function runExt(env, m, messages, opts) {
  const P = EXT[m.ext];
  const res = await fetch(P.url, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: "Bearer " + env[P.secret] },
    body: JSON.stringify({ model: m.id, messages, max_tokens: opts.maxTokens, temperature: opts.temperature, stream: opts.stream }),
    signal: AbortSignal.timeout(28000),
  });
  if (!res.ok) {                                   // текст ошибки провайдера только для разбора лимитов; ключ в него не попадает
    const t = (await res.text().catch(() => "")).slice(0, 200);
    throw new Error(`${m.ext} ${res.status} ${t}`);
  }
  return opts.stream ? res.body : await res.json();
}

async function runModel(env, m, messages, opts) {
  if (m.ext) return runExt(env, m, messages, opts);
  const base = { messages, max_tokens: opts.maxTokens, temperature: opts.temperature, stream: opts.stream };
  try {
    return await env.AI.run(m.id, base);
  } catch (e) {
    if (!m.alt) throw e;
    return await env.AI.run(m.id, { input: messages, reasoning: { effort: "low" }, max_output_tokens: opts.maxTokens, stream: opts.stream });
  }
}

async function handleChat(request, env) {
  if (env.CLOUD_ENABLED === "0") return json({ error: "disabled", message: "Облако Mico сейчас выключено." }, 503);
  const id = await verifyToken(env, request.headers.get("Authorization"));
  if (!id) return json({ error: "token", message: "Токен установки не подошёл." }, 401);
  const text = await request.text();
  if (text.length > 60000) return json({ error: "size", message: "Слишком длинный запрос." }, 413);
  let body;
  try { body = JSON.parse(text); } catch { return json({ error: "json" }, 400); }
  const messages = cleanMessages(body.messages);
  if (!messages) return json({ error: "messages", message: "Пустой или слишком большой запрос." }, 400);

  const prompt = lastUser(messages);
  const kind = detect(prompt);
  const wanted0 = LEGACY[body.mode] || body.mode;
  const wanted = TIERS.includes(wanted0) ? wanted0 : autoTier(prompt, kind);
  const maxTokens = Math.min(Math.max(Number(body.max_tokens) || 600, 16), kind === "reason" ? 1000 : 700);
  const outTok = Math.min(maxTokens, kind === "reason" ? 600 : 300);
  const inTok = estTokens(messages);
  const L = limits(env);
  let q = await standing(env, id);
  const extLeft = await extStanding(env, id);

  // Кандидаты: от нужного уровня вниз к дешёвым. В каждый берём те модели, которые влезают в остаток.
  const plan = [];
  for (let t = TIERS.indexOf(wanted); t >= 0; t--) {
    const tier = TIERS[t];
    for (const key of (CHAINS[tier][kind] || CHAINS[tier].general)) {
      const price = cost(M[key], inTok, outTok);
      const fits = M[key].ext ? (extReady(env, M[key]) && extLeft >= 1) : price <= q.left;
      if (fits && !plan.some(p => p.key === key)) plan.push({ key, tier, price });
    }
  }
  for (const key of CHEAP) {
    const price = cost(M[key], inTok, outTok);
    if (price <= q.left && !plan.some(p => p.key === key)) plan.push({ key, tier: "lite", price });
  }
  if (!plan.length) {
    const scope = q.globalLeft <= q.installLeft ? "global" : "install";
    return json({ error: "limit", scope, left: q.left, message: scope === "global"
      ? "Облако Mico на сегодня исчерпало бесплатный лимит. Загляни завтра."
      : "Ты использовал дневную долю облака Mico. Она обновится завтра." }, 429, { "retry-after": "3600", ...quotaHeaders(q) });
  }

  const opts = { maxTokens, temperature: Math.min(Math.max(Number(body.temperature ?? 0.7), 0), 1.5), stream: !!body.stream };
  let lastErr = null;
  for (const cand of plan) {
    const m = M[cand.key];
    // внешние модели списываются из своей доли (в запросах), модели Cloudflare: из доли нейронов
    const gKey = m.ext ? "ext-global" : "global", iKey = m.ext ? "ext-install:" + id : "install:" + id;
    const unit = m.ext ? 1 : cand.price, gLim = m.ext ? extLimits(env).global : L.global, iLim = m.ext ? extLimits(env).install : L.install;
    const g = await meter(env, gKey, "take", unit, gLim);
    if (!g.ok) continue;
    const inst = await meter(env, iKey, "take", unit, iLim);
    if (!inst.ok) { await meter(env, gKey, "refund", unit, gLim); continue; }
    const refund = async () => { await meter(env, gKey, "refund", unit, gLim); await meter(env, iKey, "refund", unit, iLim); };
    try {
      const res = await runModel(env, m, messages, opts);
      q = await standing(env, id);
      const info = { "x-mico-model": cand.tier, "x-mico-name": m.name, "x-mico-key": cand.key, "x-mico-cost": String(cand.price),
                     "x-mico-down": cand.tier !== wanted ? "1" : "0", ...quotaHeaders(q) };
      if (opts.stream) {
        return new Response(res, { headers: { "content-type": "text/event-stream; charset=utf-8", "cache-control": "no-store", ...info } });
      }
      const answer = stripThink(textOf(res));
      if (!answer) { await refund(); lastErr = new Error("empty"); continue; }
      return json({ text: answer, mode: cand.tier, model: m.name, key: cand.key, cost: cand.price, downgraded: cand.tier !== wanted,
                    quota: { left: q.left, install_left: q.installLeft, global_left: q.globalLeft, install_limit: q.installLimit } }, 200, info);
    } catch (e) {
      await refund();
      lastErr = e;
    }
  }
  const msg = String((lastErr && lastErr.message) || lastErr || "");
  const busy = /capacity|limit|quota|3036|exceeded|overloaded/i.test(msg);
  return json({ error: busy ? "busy" : "upstream", message: busy ? "Облако сейчас занято или лимит на сегодня кончился." : "Облако не ответило." }, busy ? 503 : 502);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      if (!env.MICO_SECRET) return json({ error: "config", message: "На сервере не задан секрет MICO_SECRET." }, 500);
      if (url.pathname === "/api/health") return json({ ok: true, enabled: env.CLOUD_ENABLED !== "0", models: Object.keys(M).length,
        providers: Object.fromEntries(Object.entries(EXT).map(([k, v]) => [k, !!env[v.secret]])) });
      if (url.pathname === "/api/register" && request.method === "POST") return handleRegister(request, env);
      if (url.pathname === "/api/chat" && request.method === "POST") return handleChat(request, env);
      if (url.pathname === "/api/quota" && request.method === "GET") return handleQuota(request, env);
      return json({ error: "not_found" }, 404);
    }
    return env.ASSETS.fetch(request);
  },
};
