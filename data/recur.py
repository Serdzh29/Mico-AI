"""Повторяющиеся напоминания: «напомни каждый понедельник в 9:00 проверить отчёт», «напомни каждый день в 8 …».
Правило хранится строкой «дни|час|минуты», где дни — номера (0 — понедельник, 6 — воскресенье)."""
import datetime, re, time

ALL = (0, 1, 2, 3, 4, 5, 6)
WORKDAYS = (0, 1, 2, 3, 4)
DAY_WORDS = {"понедельник": 0, "понедельник": 0, "вторник": 1, "среду": 2, "среда": 2, "четверг": 3,
             "пятницу": 4, "пятница": 4, "субботу": 5, "суббота": 5, "воскресенье": 6}
PAT = re.compile(r"^напомни\s+(каждый день|по будням|(?:каждый|каждую|каждое)\s+[а-я]+)\s+в\s+(\d{1,2})"
                 r"(?::(\d{2}))?\s+(.+)$")


def parse(text):
    """{'days', 'hour', 'minute', 'text'} или None, если это не повторяющееся напоминание."""
    orig = " ".join(text.split())
    s = orig.lower().replace("ё", "е")
    m = PAT.match(s)
    if not m:
        return None
    freq, hour, minute = m.group(1), int(m.group(2)), int(m.group(3) or 0)
    body_words = len(m.group(4).split())
    body = " ".join(orig.split()[-body_words:]) if body_words else ""     # текст — из оригинала, с «ё»
    if freq == "каждый день":
        days = ALL
    elif freq == "по будням":
        days = WORKDAYS
    else:
        word = freq.split()[-1]
        if word not in DAY_WORDS:
            return None
        days = (DAY_WORDS[word],)
    if not (0 <= hour <= 23 and 0 <= minute <= 59) or not body:
        return None
    return {"days": days, "hour": hour, "minute": minute, "text": body[:300]}


def encode(days, hour, minute):
    return f"{','.join(str(d) for d in days)}|{hour}|{minute}"


def decode(rule):
    days, hour, minute = rule.split("|")
    return tuple(int(d) for d in days.split(",") if d != ""), int(hour), int(minute)


def next_due(days, hour, minute, now=None):
    """Ближайший момент (timestamp), когда нужно напомнить, строго после now."""
    now = now or time.time()
    today = datetime.datetime.fromtimestamp(now).date()
    for offset in range(0, 9):
        day = today + datetime.timedelta(days=offset)
        if day.weekday() not in days:
            continue
        due = datetime.datetime(day.year, day.month, day.day, hour, minute).timestamp()
        if due > now:
            return due
    raise ValueError("нет подходящего дня")
