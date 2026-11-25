"""Календарь Mico AI: «запиши в календарь завтра в 18:30 созвон», «что у меня в календаре на неделе».
События хранятся зашифрованно в Store. За 10 минут до события Mico напоминает (через reminders).
Здесь чистая логика разбора и вывода; обращения к хранилищу — в brain.py. Проверка: tests/test_calendar.py."""
import datetime, re, time

REMIND_BEFORE = 600                 # за сколько секунд до события напомнить
DEFAULT_HOUR = 9                    # событие без времени — на 09:00 этого дня
MAX_TEXT = 200
MONTHS = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
          "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}
DAY_OFFSET = {"сегодня": 0, "завтра": 1, "послезавтра": 2}

ADD = re.compile(r"^(?:запиши|добавь|занеси|поставь)\s+(?:мне\s+)?(?:в\s+)?календар\w*\s*[:,]?\s*(?P<rest>.+)$")
LIST = re.compile(r"^(?:что\s+(?:у\s+меня\s+)?(?:там\s+)?)?(?:в\s+)?календар\w*"
                  r"(?:\s+на\s+|\s+)?(?P<when>сегодня|завтра|неделю|неделе)?$")
DELETE = re.compile(r"^(?:удали|убери)\s+(?:событие|запись)\s+(?:из\s+календар\w*\s+)?(?P<n>\d{1,6})$")


def _norm(q):
    """Пробелы и знаки по краям убираем, регистр сохраняем: имена в тексте события пишем как есть."""
    return " ".join((q or "").strip(" .!?").split())


def parse(q, now=None):
    """('add', {'due': время, 'text': текст}) | ('list', (с, по, подпись)) | ('delete', номер) |
    ('need_time', None) | None — это не про календарь."""
    now = now or time.time()
    raw = _norm(q)
    s = raw.lower().replace("ё", "е")                      # для команд — без регистра; длина строки та же
    m = DELETE.match(s)
    if m:
        return "delete", int(m.group("n"))
    m = LIST.match(s)
    if m:
        return "list", _list_range(m.group("when"), now)
    m = ADD.match(s)
    if m:
        ev = _event(raw[m.start("rest"):m.end("rest")], now)
        return ev if ev else ("need_time", None)
    return None


def _list_range(when, now):
    today0 = _day_start(now)
    if when in ("неделю", "неделе"):
        return today0, today0 + 7 * 86400, "на неделю"
    if when == "завтра":
        return today0 + 86400, today0 + 2 * 86400, "на завтра"
    return today0, today0 + 86400, "на сегодня"


def _day_start(ts):
    lt = time.localtime(ts)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def _event(rest, now):
    """Вытаскивает время, дату и текст. None — нет ни даты, ни времени (тогда спросим время).
    Время разбираем раньше даты: «в 18.30» не должно стать датой 18 числа."""
    s = rest
    hour = minute = None
    m = re.search(r"\bв\s+(\d{1,2})[:.](\d{2})\b", s, re.I)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        s = _cut(s, m)
    else:
        m = re.search(r"\bв\s+(\d{1,2})(?:\s*час\w*)?(?:\s+(утра|вечера|дня|ночи))?\b", s, re.I)
        if m:
            hour, minute = _hour12(int(m.group(1)), (m.group(2) or "").lower()), 0
            s = _cut(s, m)
    day = None
    m = re.search(r"\b(сегодня|завтра|послезавтра)\b", s, re.I)
    if m:
        day = datetime.date.fromtimestamp(now) + datetime.timedelta(days=DAY_OFFSET[m.group(1).lower()])
        s = _cut(s, m)
    if day is None:
        m = re.search(r"\b(\d{1,2})\s+(" + "|".join(MONTHS) + r")\b", s, re.I)
        if m:
            day = _date(int(m.group(1)), MONTHS[m.group(2).lower()], None, now)
            s = _cut(s, m)
    if day is None:
        m = re.search(r"\b(\d{1,2})[.](\d{1,2})(?:[.](\d{4}|\d{2}))?\b", s)
        if m:
            year = m.group(3)
            if year and len(year) == 2:
                year = "20" + year
            day = _date(int(m.group(1)), int(m.group(2)), int(year) if year else None, now)
            s = _cut(s, m)
    if day is None and hour is None:
        return None
    if hour is None:
        hour, minute = DEFAULT_HOUR, 0
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None
    text = " ".join(re.sub(r"^(в|на|о)\s+", "", " ".join(s.split()), flags=re.I).split())[:MAX_TEXT]
    if not text:
        text = "событие"
    if day is None:                                          # только время — сегодня, а если уже прошло, то завтра
        day = datetime.date.fromtimestamp(now)
        due = _at(day, hour, minute)
        if due <= now:
            due = _at(day + datetime.timedelta(days=1), hour, minute)
    else:
        due = _at(day, hour, minute)
    return "add", {"due": int(due), "text": text}


def _cut(s, m):
    return (s[:m.start()] + " " + s[m.end():]).strip()


def _hour12(h, part):
    """«в 6 вечера» → 18; «в 12 ночи» → 0."""
    if part in ("вечера", "дня") and h < 12:
        return h + 12
    if part == "ночи" and h == 12:
        return 0
    return h


def _date(d, mon, year, now):
    today = datetime.date.fromtimestamp(now)
    y = year or today.year
    try:
        day = datetime.date(y, mon, d)
    except ValueError:
        return None
    if year is None and day < today:                         # «15 ноября», когда ноябрь уже прошёл — это следующий год
        try:
            day = datetime.date(y + 1, mon, d)
        except ValueError:
            return None
    return day


def _at(day, hour, minute):
    return time.mktime((day.year, day.month, day.day, hour, minute, 0, 0, 0, -1))


def fmt_when(due):
    return time.strftime("%d.%m в %H:%M", time.localtime(due))


def format_list(events, label):
    """events — [(id, due, text)] в порядке времени."""
    if not events:
        return f"В календаре {label} пусто."
    lines = [f"В календаре {label}:"]
    for eid, due, text in events:
        lines.append(f"• {fmt_when(due)} — {text}  (№{eid})")
    lines.append("Удалить событие: «удали событие N».")
    return "\n".join(lines)


def reminder_time(due, now):
    """Когда напомнить: за REMIND_BEFORE до события. None — уже поздно (событие почти сейчас)."""
    at = due - REMIND_BEFORE
    return at if at > now else None
