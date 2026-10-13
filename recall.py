"""Вспоминание разговора: «о чём мы говорили вчера», «что я спрашивал на прошлой неделе»,
«о чём говорили про принтер». Берёт сохранённые реплики и показывает их по времени.
Модель не нужна: ответ собирается из самих реплик. Чистая логика — проверяется в tests/test_recall.py."""
import re, time

DAY = 86400
MEMORY = r"(говорил\w*|разговаривал\w*|обсуждал\w*|спрашивал\w*|писал\w*|рассказывал\w*)"
ASK = re.compile(r"\b(о\s+чем|про\s+что|что)\b[^?.!]{0,25}?\b" + MEMORY + r"\b"
                 r"|\b(помнишь|вспомни|вспоминаешь)\b[^?.!]{0,30}?\b(говорил\w*|спрашивал\w*|писал\w*|обсуждал\w*"
                 r"|разговаривал\w*|вчера|сегодня|позавчера|недел\w*|про)\b")
TOPIC_STOP = set("вчера сегодня позавчера неделю неделе неделя дня дней дня день последние последнюю "
                 "прошлой прошлую за мы ты тебе тобой со с говорили говорил спрашивал писал".split())
LIMIT = 8                                      # сколько пар «вопрос — ответ» показывать


def _norm(s):
    return s.lower().replace("ё", "е")


def window(q, now):
    """(начало, конец, как назвать период) по словам из фразы."""
    s = _norm(q)
    lt = time.localtime(now)
    today0 = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
    if "позавчера" in s:
        return today0 - 2 * DAY, today0 - DAY, "позавчера"
    if "вчера" in s:
        return today0 - DAY, today0, "вчера"
    if "сегодня" in s:
        return today0, now + 1, "сегодня"
    m = re.search(r"за\s+последн\w*\s+(\d{1,2})\s+дн", s)
    if m:
        n = max(1, min(int(m.group(1)), 90))
        return now - n * DAY, now + 1, f"за последние {n} дн."
    if re.search(r"прошл\w+\s+недел|за\s+недел", s):
        return now - 7 * DAY, now + 1, "за прошлую неделю"
    return now - 7 * DAY, now + 1, "за последнюю неделю"


def topic_of(q):
    """Слова после «про …» без слов о времени. None — тема не названа."""
    m = re.search(r"\bпро\s+(.+)$", _norm(q).strip(" ?!."))
    if not m:
        return None
    words = [w for w in re.findall(r"[а-яa-z0-9]+", m.group(1)) if len(w) >= 3 and w not in TOPIC_STOP]
    return words or None


def parse(q, now=None):
    """None — это не просьба вспомнить. Иначе — период и тема."""
    now = now or time.time()
    if not ASK.search(_norm(q)):
        return None
    t0, t1, label = window(q, now)
    return {"t0": t0, "t1": t1, "label": label, "topic": topic_of(q)}


def pairs(rows):
    """Реплики [(время, роль, текст)] → пары (время, вопрос, ответ). Ответы Mico без вопроса пропускаем."""
    rows = sorted(rows)
    out, i = [], 0
    while i < len(rows):
        ts, role, text = rows[i]
        if role == "user":
            reply = ""
            if i + 1 < len(rows) and rows[i + 1][1] == "mico":
                reply = rows[i + 1][2]
                i += 1
            out.append((ts, text, reply))
        i += 1
    return out


def _mentions(text, words):
    t = _norm(text)
    return any(w[:5] in t for w in words)          # «принтер» находит «принтеры», «принтера»


def _clip(s, n=110):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n - 1] + "…"


def answer(rows, spec, limit=LIMIT):
    found = pairs(rows)
    topic = spec.get("topic")
    if topic:
        found = [p for p in found if _mentions(p[1] + " " + p[2], topic)]
    where = spec["label"] + (f" про «{' '.join(topic)}»" if topic else "")
    if not found:
        return f"{where[:1].upper() + where[1:]} ничего не нашёл. Возможно, тогда мы ещё не разговаривали или я не сохранил."
    shown = found[-limit:]
    lines = [f"Вот что мы говорили {where}:"]
    if len(found) > len(shown):
        lines.append(f"(показываю последние {len(shown)} из {len(found)})")
    for ts, q, a in shown:
        when = time.strftime("%d.%m %H:%M", time.localtime(ts))
        lines.append(f"• {when} — ты: {_clip(q)}")
        if a:
            lines.append(f"   Mico: {_clip(a)}")
    return "\n".join(lines)
