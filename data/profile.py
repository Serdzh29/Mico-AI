"""Портрет пользователя: короткие факты о привычках, которые Mico AI подтвердил повторами.

Правила (пункт 2 плана):
- факт попадает в профиль, только если паттерн повторился не меньше MIN_REPEATS раз;
- у каждого факта есть источник («откуда узнали») и статус: подтверждён или ждёт подтверждения;
- в промпт модели попадают только подтверждённые факты, относящиеся к вопросу, и не больше MAX_IN_PROMPT;
- пользователь видит список, может подтвердить или удалить факт; удалённый сам не возвращается;
- факты из разговора (пункт 3) сначала ждут подтверждения и никуда не попадают без него.

Источники: журнал окон (программы), нажатия кнопок под чатом. Факты из разговора приходят
через модель (extract_prompt / parse_candidates). Хранение — зашифрованная таблица profile в Store.
Чистая логика: без Qt, без Windows и без модели. Проверяется в tests/test_user_profile.py."""
import hashlib, json, re, time

from core import memory

MIN_REPEATS = 3              # сколько раз паттерн должен повториться, чтобы стать фактом
MAX_IN_PROMPT = 2            # сколько фактов добавлять в один запрос к модели
PROGRAM_DAY_SEC = 600        # программа считается «использованной за день», если открыта хотя бы 10 минут
WINDOW_DAYS = 14             # за какой период смотрим журнал окон
CANDIDATE_DAYS = 14          # неподтверждённые предложения живут две недели: не подтвердили — забываем
MAX_FACTS = 30               # всего фактов в профиле
MAX_PENDING = 8              # ждущих подтверждения
MAX_FACT_LEN = 120
MAX_FORGOTTEN = 200
CONFIRMED, PENDING = "confirmed", "pending"
SOURCE_CONV = "разговор"
SOURCE_SELF = "твои слова"       # факт, который пользователь сам сказал о себе в чате: сразу подтверждён
SELF_IN_PROMPT = 3               # сколько таких фактов добавлять в каждый запрос к модели

SYSTEM_PROCS = {"explorer.exe", "searchhost.exe", "shellexperiencehost.exe", "applicationframehost.exe",
                "dwm.exe", "python.exe", "pythonw.exe", "runtimebroker.exe", "sihost.exe", "ctfmon.exe"}
BROWSERS = {"chrome.exe": "chrome", "msedge.exe": "edge", "firefox.exe": "firefox", "yandex.exe": "яндекс браузер",
            "opera.exe": "opera", "brave.exe": "brave"}
PROGRAM_WORDS = re.compile(r"откр|запусти|запуск|зайд|перейд|покаж", re.IGNORECASE)
BROWSER_WORDS = re.compile(r"браузер|хром|chrome|edge|эдж|firefox|фаерфокс|яндекс|opera|опер|интернет|сайт",
                           re.IGNORECASE)
# в факты не пишем: пароли, адреса, здоровье, финансы, контакты других людей
SENSITIVE = re.compile(r"парол|пин-|карт[ыу]\b|счёт|счет\b|адрес|диагноз|болез|здоровь|лекарств|врач|депресс|"
                       r"кредит|долг|паспорт|телефон|@|неделю|сегодня|вчера", re.IGNORECASE)

EXTRACT_PROMPT = ("Ниже последние реплики разговора. Найди устойчивые факты о самом пользователе, которые он сам назвал: "
                  "профессия, постоянные занятия, предпочтения, программы, которыми он пользуется. Не выдумывай. "
                  "Не записывай временное состояние, пароли, адреса, здоровье, деньги и данные других людей. "
                  "Ответь ТОЛЬКО JSON вида {{\"facts\": [\"короткий факт по-русски\"]}}. Если фактов нет — {{\"facts\": []}}.\n\n"
                  "Реплики:\n{lines}")


def _key_hash(text):
    return hashlib.sha256(text.lower().encode("utf-8")).hexdigest()[:16]


def _fact(key, text, evidence, tags, source, status, count=0):
    return {"key": key, "text": text[:MAX_FACT_LEN], "evidence": evidence, "tags": list(tags),
            "source": source, "status": status, "count": int(count), "ts": time.time()}


def empty():
    return {"facts": [], "forgotten": []}


# ---------- факты из данных Mico AI (повторы, не единичные действия) ----------
def program_facts(rows):
    """rows — (начало, конец, процесс) из журнала окон. Программа — факт, если открыта не меньше
    MIN_REPEATS разных дней (не меньше PROGRAM_DAY_SEC в день)."""
    per_day = {}
    for start, end, proc in rows:
        p = (proc or "").lower()
        if not p or p in SYSTEM_PROCS or "host" in p or p.startswith("mico"):
            continue
        day = time.strftime("%Y-%m-%d", time.localtime(start))
        per_day.setdefault(p, {})
        per_day[p][day] = per_day[p].get(day, 0) + max(0, end - start)
    facts = []
    for proc, days in per_day.items():
        using = [d for d, secs in days.items() if secs >= PROGRAM_DAY_SEC]
        if len(using) < MIN_REPEATS:
            continue
        tags = ["program"] + (["browser"] if proc in BROWSERS else [])
        facts.append(_fact(
            key=f"prog:{proc}", text=f"Часто работаешь в «{memory.pretty(proc)}»",
            evidence=f"открывал не меньше {MIN_REPEATS} дней за последние {WINDOW_DAYS} (журнал окон)",
            tags=tags, source="программы", status=CONFIRMED, count=len(using)))
    return facts


def chip_facts(usage, labels):
    """usage — {id кнопки: сколько раз}; labels — {id: подпись}. Только частые нажатия."""
    facts = []
    for cid, n in (usage or {}).items():
        if n >= MIN_REPEATS and cid in labels:
            facts.append(_fact(key=f"chip:{cid}", text=f"Часто пользуешься кнопкой «{labels[cid]}»",
                               evidence=f"нажимал или просил {n} раз (кнопки под чатом и команды)",
                               tags=["chip"], source="кнопки", status=CONFIRMED, count=n))
    return facts


# ---------- факты из разговора: только предложения, без записи до подтверждения ----------
def parse_candidates(raw):
    """Ответ модели → список коротких фактов. Всё, что похоже на чувствительное или мусор, отбрасываем."""
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return []
    items = data.get("facts") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    out = []
    for it in items:
        if not isinstance(it, str):
            continue
        text = " ".join(it.split())[:MAX_FACT_LEN]
        if len(text) < 6 or SENSITIVE.search(text):
            continue
        out.append(text)
    return out[:5]


def candidate_facts(texts):
    out = []
    for text in texts:
        tags = ["browser"] if BROWSER_WORDS.search(text) else ["general"]
        out.append(_fact(key="conv:" + _key_hash(text), text=text,
                         evidence="из разговора, нужно твоё подтверждение", tags=tags,
                         source=SOURCE_CONV, status=PENDING, count=1))
    return out


# ---------- то, что пользователь сказал о себе прямо в чате ----------
# Только явные фразы о себе. Ничего не выводим из догадок: они остаются в журнале, а не в профиле.
SELF_NAME = re.compile(r"^меня зовут\s+(?P<n>[а-яa-z-]{2,30})\b")
SELF_TOPIC = re.compile(r"\bя\s+(?P<verb>работаю|учусь|занимаюсь|увлекаюсь|преподаю|программирую|рисую|"
                        r"пишу\s+музыку|играю\s+в|люблю|пользуюсь)\b(?P<rest>[^.!?]{0,80})")
SELF_EXPLICIT = re.compile(r"^запомни,?\s+что\s+(?P<s>(?:я|у меня|мне|меня)\s.{3,140})$")
SELF_LEN = (6, MAX_FACT_LEN)
# личное, что в факт о себе не попадает: где живёт, контакты, деньги, здоровье, семья
SELF_SENSITIVE = re.compile(r"живу|живёт|проживаю|улиц|проспект|квартир|адрес|\bдом\b|номер|телефон|почт|@|"
                            r"пароль|карт[ауы]\b|банк|зарплат|долг|кредит|болею|болезн|диагноз|врач|беремен|"
                            r"развод|умер|жена|муж|дет(?:ей|и|ь|ям)\b|ребён|двое\b|трое\b|тебя|тебе|тобой|\bты\b", re.IGNORECASE)


def parse_self_statement(q):
    """Что пользователь сказал о себе прямо. None — ничего похожего. (текст факта, просил ли запомнить явно)."""
    s = " ".join((q or "").lower().replace("ё", "е").strip(" .!?").split())
    if not s:
        return None
    m = SELF_EXPLICIT.match(s)
    if m:
        text = "Пользователь попросил запомнить: «" + m.group("s")[:120] + "»"
        explicit = True
    else:
        m = SELF_NAME.match(s)
        if m:
            text = "Пользователя зовут " + m.group("n").capitalize()
        else:
            m = SELF_TOPIC.search(s)
            if not m:
                return None
            sentence = (m.group("verb") + m.group("rest")).strip()
            text = "Пользователь сказал: «я " + sentence[:100] + "»"
        explicit = False
    if not (SELF_LEN[0] <= len(text) <= SELF_LEN[1]) or SENSITIVE.search(text) or SELF_SENSITIVE.search(text):
        return None
    return text, explicit


def self_fact(text):
    """Факт из слов пользователя: сразу подтверждён, потому что он сам это сказал."""
    return _fact(key="self:" + _key_hash(text), text=text, evidence="ты сам сказал об этом в чате",
                 tags=["self", "general"], source=SOURCE_SELF, status=CONFIRMED, count=1)


def add_self_fact(profile, fact):
    """Добавляет факт о себе. Если его удаляли раньше, а пользователь сказал это снова — возвращаем."""
    profile["forgotten"] = [k for k in profile.get("forgotten", []) if k != fact["key"]]
    facts = [f for f in profile.get("facts", []) if f["key"] != fact["key"]]
    facts.append(fact)
    profile["facts"] = facts[-MAX_FACTS:]
    return profile


# ---------- слияние и хранение ----------
def merge(profile, auto=None, candidates=()):
    """Обновляет профиль. auto=None — автофакты не трогаем (например, добавили факт из разговора).
    Если auto передан — автофакты пересчитываются заново: исчезнувшие (ниже порога) убираются.
    Факты из разговора сохраняются. Удалённые пользователем не возвращаются."""
    forgotten = set(profile.get("forgotten", []))
    if auto is None:
        by_key = {f["key"]: f for f in profile.get("facts", [])}
    else:
        keep = (SOURCE_CONV, SOURCE_SELF)                  # то, что сказал пользователь, пересчёт не трогает
        by_key = {f["key"]: f for f in profile.get("facts", []) if f["source"] in keep}
        for f in auto:
            if f["key"] not in forgotten:
                by_key[f["key"]] = f
    pending = sum(1 for f in by_key.values() if f["status"] == PENDING)
    for f in candidates:
        if f["key"] in forgotten or f["key"] in by_key or pending >= MAX_PENDING:
            continue
        by_key[f["key"]] = f
        pending += 1
    profile["facts"] = list(by_key.values())[-MAX_FACTS:]
    return profile


def forget_old(profile, now=None):
    """Забывание мелочей: предложения, которые так и не подтвердили, уходят через две недели.
    Подтверждённые факты не трогаем — их удаляет сам пользователь в панели «Что Mico AI знает»."""
    now = now or time.time()
    facts = profile.get("facts", [])
    keep = [f for f in facts if f["status"] != PENDING
            or not f.get("ts") or now - f["ts"] <= CANDIDATE_DAYS * 86400]
    dropped = len(facts) - len(keep)
    if dropped:
        profile["facts"] = keep
    return dropped


def touch(facts):
    """Факты вошли в промпт: они полезны и выше поднимаются в приоритете."""
    for f in facts:
        f["count"] = int(f.get("count", 0)) + 1
    return facts


def relevant(profile, question, limit=MAX_IN_PROMPT):
    """Факты, которые стоит добавить к этому вопросу. Только подтверждённые; «чип»-факты не в промпт.
    Подходят, если тема вопроса совпадает (программы, браузер) или есть общее слово."""
    q = (question or "").lower().replace("ё", "е")
    if not q.strip():
        return []
    topics = set()
    if PROGRAM_WORDS.search(q):
        topics.add("program")
    if BROWSER_WORDS.search(q):
        topics.add("browser")
    stems = {w[:5] for w in re.findall(r"[а-яa-z0-9]+", q) if len(w) >= 4}
    picked, selfs = [], []
    for f in profile.get("facts", []):
        if f["status"] != CONFIRMED or "chip" in f["tags"]:
            continue
        if "self" in f["tags"]:                            # сказал сам о себе: помним всегда, последние
            selfs.append(f)
            continue
        by_topic = bool(topics & set(f["tags"]))
        words = {w[:5] for w in re.findall(r"[а-яa-z0-9]+", f["text"].lower().replace("ё", "е")) if len(w) >= 4}
        if by_topic or (stems & words):
            picked.append(f)
    picked.sort(key=lambda f: int(f.get("count", 0)), reverse=True)   # полезные факты — впереди
    return selfs[-SELF_IN_PROMPT:] + picked[:limit]


def prompt_line(facts):
    if not facts:
        return ""
    return ("Известно о пользователе (учитывай, только если это относится к вопросу, "
            "не пересказывай): " + "; ".join(f["text"] for f in facts) + ".")


def preferred_browser(profile):
    """Какой браузер пользователь открывает чаще всего (по подтверждённым фактам). None — не знаем."""
    best = None
    for f in profile.get("facts", []):
        if f["status"] == CONFIRMED and f["key"].startswith("prog:") and "browser" in f["tags"]:
            if best is None or f["count"] > best["count"]:
                best = f
    return BROWSERS.get(best["key"][5:]) if best else None


def extract_prompt(lines):
    return EXTRACT_PROMPT.format(lines=lines)


# ---------- команды «что ты обо мне знаешь» ----------
def parse_command(q):
    s = " ".join((q or "").lower().replace("ё", "е").strip(" .!?").split())
    if re.fullmatch(r"(что|чего)\s+(ты\s+)?(знаешь|помнишь)\s+обо\s+мне"
                    r"|что\s+ты\s+обо\s+мне\s+(знаешь|помнишь)"
                    r"|что\s+ты\s+(знаешь|помнишь)\s+обо\s+мне"
                    r"|покажи\s+(мой\s+)?профиль", s):
        return ("list", None)
    m = re.fullmatch(r"подтверди(?:ть)?\s+факт\s+(\d{1,2})", s)
    if m:
        return ("confirm", int(m.group(1)))
    m = re.fullmatch(r"(?:забудь|удали|удалить)\s+факт\s+(\d{1,2})", s)
    if m:
        return ("forget", int(m.group(1)))
    if re.fullmatch(r"(?:забудь|удали|удалить)\s+(?:всё|все)\s+(?:обо\s+мне|про\s+меня)", s):
        return ("forget_all", None)
    return None


def describe_list(profile):
    facts = profile.get("facts", [])
    if not facts:
        return ("Пока ничего не знаю о твоих привычках. Запоминаю только то, что повторяется не меньше "
                f"{MIN_REPEATS} раз.")
    lines = ["Вот что я знаю о тебе:"]
    for i, f in enumerate(facts, 1):
        mark = "❔" if f["status"] == PENDING else "✓"
        lines.append(f"{i}. {mark} {f['text']} — {f['evidence']}")
    lines.append("Подтвердить: «подтверди факт N». Удалить: «забудь факт N». Всё: «забудь всё обо мне».")
    return "\n".join(lines)


def apply_command(profile, cmd, arg=None):
    """Выполняет команду над профилем. Возвращает (профиль, текст ответа)."""
    facts = profile["facts"]
    if cmd == "list":
        return profile, describe_list(profile)
    if cmd in ("confirm", "forget"):
        if not 1 <= arg <= len(facts):
            return profile, f"Нет факта с номером {arg}. Посмотри список: «что ты обо мне знаешь»."
        f = facts[arg - 1]
        if cmd == "confirm":
            if f["status"] == CONFIRMED:
                return profile, "Этот факт уже подтверждён."
            f["status"] = CONFIRMED
            return profile, f"Подтвердил: «{f['text']}»."
        facts.pop(arg - 1)
        profile["forgotten"] = (profile.get("forgotten", []) + [f["key"]])[-MAX_FORGOTTEN:]
        return profile, f"Забыл: «{f['text']}»."
    if cmd == "forget_all":
        profile["forgotten"] = (profile.get("forgotten", []) + [f["key"] for f in facts])[-MAX_FORGOTTEN:]
        profile["facts"] = []
        return profile, "Забыл всё, что знал о твоих привычках. Новое появится, только если повторится."
    raise ValueError(cmd)
