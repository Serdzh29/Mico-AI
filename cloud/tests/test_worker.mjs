import assert from "node:assert/strict";
const mod = await import("../src/worker.js");
const worker = mod.default, Meter = mod.Meter;

function makeEnv(over = {}) {
  const objs = new Map();
  const METER = { idFromName: n => n, get: n => { if (!objs.has(n)) { const store = new Map(); objs.set(n, new Meter({ storage: { get: async k => store.get(k), put: async (k, v) => store.set(k, v) } })); } const o = objs.get(n); return { fetch: (u, init) => o.fetch(new Request(u, init)) }; } };
  const calls = [];
  const state = { fail: new Set(), rejectMessages: new Set() };
  const AI = { run: async (model, p) => {
    calls.push({ model, p });
    if (state.fail.has(model)) throw new Error("model down");
    if (p.messages && [...state.rejectMessages].some(x => model.includes(x))) throw new Error("messages not supported");
    if (p.stream) return new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode('data: {"response":"При"}\n\ndata: {"response":"вет"}\n\ndata: [DONE]\n\n')); c.close(); } });
    if (p.input) return { output: [{ content: [{ text: "ответ через input" }] }] };
    return { response: "<think>думаю</think>Привет!" };
  } };
  const env = { MICO_SECRET: "s3cret", AI, METER, ASSETS: { fetch: async () => new Response("site") }, INSTALL_NEURONS_DAY: "5000", GLOBAL_NEURONS_DAY: "50000", REGISTER_PER_IP_DAY: "99", ...over };
  const call = (path, body, token, method = "POST") => worker.fetch(new Request("https://x" + path, { method, headers: { "content-type": "application/json", ...(token ? { authorization: "Bearer " + token } : {}), "CF-Connecting-IP": "1.2.3.4" }, body: body && method !== "GET" ? JSON.stringify(body) : undefined }), env);
  const reg = async () => (await (await call("/api/register")).json()).token;
  return { env, calls, state, call, reg };
}
const msg = t => [{ role: "system", content: "ты Mico" }, { role: "user", content: t }];

// --- сайт, здоровье, токены
{
  const { call, reg } = makeEnv();
  assert.equal((await call("/", null, null, "GET")).status, 200);
  const h = await (await call("/api/health", null, null, "GET")).json();
  assert.equal(h.ok, true); assert.ok(h.models >= 14, "в каталоге не меньше 14 лучших моделей");
  const token = await reg();
  assert.match(token, /^[0-9a-f]{32}\.[0-9a-f]{64}$/);
  assert.equal((await call("/api/chat", { messages: msg("привет") }, "bad.token")).status, 401);
  assert.equal((await call("/api/quota", null, "bad", "GET")).status, 401);
}
// --- режим Авто выбирает уровень и модель; ответ очищен от «думаю»
{
  const { call, calls, reg } = makeEnv();
  const t = await reg();
  const ask = async (q, mode = "auto") => { const r = await call("/api/chat", { messages: msg(q), mode }, t); assert.equal(r.status, 200, q); return r.json(); };
  let j = await ask("как дела?");
  assert.equal(j.mode, "lite"); assert.equal(j.key, "l31_8b"); assert.equal(j.text, "Привет!");
  j = await ask("объясни, почему небо голубое"); assert.equal(j.mode, "plus"); assert.equal(j.key, "l33");
  j = await ask("напиши функцию на python для сортировки"); assert.equal(j.mode, "plus"); assert.equal(j.key, "coder");
  j = await ask("напиши стих про осень"); assert.equal(j.mode, "lite"); assert.equal(j.key, "gm4");
  j = await ask("докажи строго, что корень из двух иррационален"); assert.equal(j.mode, "max"); assert.equal(j.key, "dsp");
  j = await ask("привет", "max"); assert.equal(j.mode, "max"); assert.equal(j.key, "k26");
  j = await ask("привет", "plus"); assert.equal(j.mode, "plus"); assert.equal(j.key, "l33");
  j = await ask("привет", "lite"); assert.equal(j.mode, "lite");
  j = await ask("привет", "fast"); assert.equal(j.mode, "lite");            // старые режимы прежних версий
  j = await ask("привет", "basic"); assert.equal(j.mode, "lite");
  j = await ask("привет", "pro"); assert.equal(j.mode, "plus");
  j = await ask("привет", "ultra"); assert.equal(j.mode, "max");
  j = await ask("привет", "smart"); assert.equal(j.mode, "plus");
}
// --- остаток считается и пересчитывается после каждого запроса
{
  const { call, reg } = makeEnv({ INSTALL_NEURONS_DAY: "1000" });
  const t = await reg();
  let qa = await (await call("/api/quota", null, t, "GET")).json();
  assert.equal(qa.left, 1000); assert.ok(qa.tiers.lite.cost < qa.tiers.plus.cost && qa.tiers.plus.cost < qa.tiers.max.cost);
  assert.ok(qa.models.length >= 14 && qa.models.every(m => m.cost > 0));
  const r = await call("/api/chat", { messages: msg("как дела?"), mode: "lite" }, t); const j = await r.json();
  qa = await (await call("/api/quota", null, t, "GET")).json();
  assert.equal(qa.left, 1000 - j.cost, "остаток уменьшился ровно на цену запроса");
  assert.equal(Number(r.headers.get("x-mico-left")), qa.left); assert.equal(j.quota.left, qa.left);
}
// --- дорогой уровень не влезает: понижаем и сообщаем об этом; совсем нет доли: 429
{
  const { call, reg } = makeEnv({ INSTALL_NEURONS_DAY: "60" });
  const t = await reg();
  let r = await call("/api/chat", { messages: msg("привет"), mode: "max" }, t); let j = await r.json();
  assert.equal(r.status, 200); assert.equal(j.downgraded, true); assert.notEqual(j.mode, "max");
  for (let i = 0; i < 60; i++) { r = await call("/api/chat", { messages: msg("привет " + i), mode: "lite" }, t); if (r.status === 429) break; }
  assert.equal(r.status, 429); assert.equal((await r.json()).scope, "install");
}
// --- сбой модели: пробуем следующую и возвращаем потраченное
{
  const { call, calls, state, reg } = makeEnv({ INSTALL_NEURONS_DAY: "1000" });
  const t = await reg();
  state.fail.add("@cf/meta/llama-3.1-8b-instruct-fp8-fast");
  let r = await call("/api/chat", { messages: msg("как дела?"), mode: "lite" }, t); let j = await r.json();
  assert.equal(r.status, 200); assert.equal(j.key, "glm47f");
  const qa = await (await call("/api/quota", null, t, "GET")).json();
  assert.equal(qa.left, 1000 - j.cost, "за сбойную модель ничего не списано");
  for (const id of ["@cf/zai-org/glm-4.7-flash", "@cf/meta/llama-3.2-3b-instruct", "@cf/google/gemma-4-26b-a4b-it"]) state.fail.add(id);
  r = await call("/api/chat", { messages: msg("как дела?"), mode: "lite" }, t);
  assert.equal(r.status, 502);
}
// --- gpt-oss: если «messages» не принят, пробуется формат «input»
{
  const { call, state, reg } = makeEnv();
  const t = await reg();
  state.rejectMessages.add("gpt-oss");
  const r = await call("/api/chat", { messages: msg("реши задачу про два поезда, которые выезжают из разных городов навстречу друг другу с разными скоростями, и найди время встречи"), mode: "auto" }, t);
  const j = await r.json();
  assert.equal(r.status, 200); assert.equal(j.key, "oss120"); assert.equal(j.text, "ответ через input");
}
// --- потоковый ответ с заголовками остатка
{
  const { call, reg } = makeEnv();
  const t = await reg();
  const r = await call("/api/chat", { messages: msg("привет"), stream: true, mode: "lite" }, t);
  assert.match(r.headers.get("content-type"), /event-stream/);
  assert.ok(Number(r.headers.get("x-mico-left")) > 0 && r.headers.get("x-mico-name"));
  assert.match(await r.text(), /"response":"При"/);
}
// --- выключатель и пустой запрос
{
  const { env, call, reg } = makeEnv();
  const t = await reg();
  assert.equal((await call("/api/chat", { messages: [] }, t)).status, 400);
  env.CLOUD_ENABLED = "0"; assert.equal((await call("/api/chat", { messages: msg("x") }, t)).status, 503);
}
// --- внешние источники: Groq, Gemini, NVIDIA (только при заданном секрете), своя доля в запросах
{
  const realFetch = globalThis.fetch, seen = [];
  const fail = new Set();
  globalThis.fetch = async (url, init) => {
    const b = JSON.parse(init.body);
    seen.push({ url: String(url), model: b.model, auth: init.headers.authorization, stream: b.stream });
    if ([...fail].some(x => String(url).includes(x))) return new Response("rate limit", { status: 429 });
    if (b.stream) return new Response('data: {"choices":[{"delta":{"content":"Привет"}}]}\n\ndata: [DONE]\n\n');
    return new Response(JSON.stringify({ choices: [{ message: { content: "ответ " + b.model } }] }), { headers: { "content-type": "application/json" } });
  };
  try {
    // без секретов внешние модели не используются и не видны в /api/quota
    let e = makeEnv(); let t = await e.reg();
    let j = await (await e.call("/api/chat", { messages: msg("как дела?"), mode: "lite" }, t)).json();
    assert.equal(j.key, "l31_8b"); assert.equal(seen.length, 0);
    const qa = await (await e.call("/api/quota", null, t, "GET")).json();
    assert.ok(qa.models.every(m => !/^(gq|gem|nv)_/.test(m.key)));
    // с секретами: уровни берут Groq, Gemini и NVIDIA по цепочкам
    e = makeEnv({ GROQ_API_KEY: "g", GEMINI_API_KEY: "m", NVIDIA_API_KEY: "n" }); t = await e.reg();
    const h = await (await e.call("/api/health", null, null, "GET")).json();
    assert.deepEqual(h.providers, { groq: true, gemini: true, nvidia: true });
    j = await (await e.call("/api/chat", { messages: msg("привет"), mode: "lite" }, t)).json();
    assert.equal(j.key, "gq_8b"); assert.equal(j.text, "ответ llama-3.1-8b-instant"); assert.equal(j.cost, 0);
    assert.match(seen.at(-1).url, /api\.groq\.com/); assert.equal(seen.at(-1).auth, "Bearer g");
    j = await (await e.call("/api/chat", { messages: msg("привет"), mode: "max" }, t)).json();
    assert.equal(j.key, "gem_pro"); assert.match(seen.at(-1).url, /generativelanguage/); assert.equal(seen.at(-1).auth, "Bearer m");
    // сбой Gemini (429): пробуется следующий кандидат, а не ошибка
    fail.add("generativelanguage");
    j = await (await e.call("/api/chat", { messages: msg("привет"), mode: "max" }, t)).json();
    assert.equal(j.key, "k26");
    // у Groq тоже сбой: Plus уходит на Cloudflare или NVIDIA
    fail.add("api.groq.com");
    j = await (await e.call("/api/chat", { messages: msg("объясни, почему небо голубое"), mode: "plus" }, t)).json();
    assert.equal(j.key, "l33");
    // потоковый ответ идёт как есть, в формате OpenAI
    fail.clear();
    const r = await e.call("/api/chat", { messages: msg("привет"), mode: "plus", stream: true }, t);
    assert.equal(r.status, 200); assert.match(await r.text(), /"content":"Привет"/);
    // доля внешних источников: после лимита идут модели Cloudflare, нейроны не тратятся на внешние
    e = makeEnv({ GROQ_API_KEY: "g", EXT_INSTALL_DAY: "2" }); t = await e.reg();
    const keys = [];
    for (let i = 0; i < 3; i++) keys.push((await (await e.call("/api/chat", { messages: msg("привет"), mode: "lite" }, t)).json()).key);
    assert.deepEqual(keys, ["gq_8b", "gq_8b", "l31_8b"]);
  } finally { globalThis.fetch = realFetch; }
}
console.log("worker ok");
