"""Расписание переключателей (бета): «тёмная тема после 21:00», «не беспокоить с 23:00 до 08:00».
Разрешены только действия, которые Mico уже умеет выполнять по фразе (включи/выключи какой-то переключатель или тему)."""
import re, time

ONE = re.compile(r"^(включи|выключи)\s+(.+?)\s+(?:в|после)\s+(\d{1,2})[:.](\d{2})$")
RANGE = re.compile(r"^(?:включи\s+)?(.+?)\s+с\s+(\d{1,2})[:.](\d{2})\s+до\s+(\d{1,2})[:.](\d{2})$")
THEME_ONE = re.compile(r"^(тем\w+|светл\w+)\s+тем\w+\s+(?:в|после)\s+(\d{1,2})[:.](\d{2})$")


def _hm(h, m):
    h, m = int(h), int(m)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError
    return f"{h:02d}:{m:02d}"


def parse(ql, valid):
    """[(фраза-действие, 'HH:MM')] или None. valid(фраза) -> True, если Mico умеет такое действие."""
    s = (ql or "").strip(" .!?").replace("ё", "е")
    try:
        m = ONE.match(s)
        if m:
            action = f"{m.group(1)} {m.group(2)}"
            return [(action, _hm(m.group(3), m.group(4)))] if valid(action) else None
        m = THEME_ONE.match(s)
        if m:
            action = "включи темную тему" if m.group(1).startswith("тем") else "включи светлую тему"
            return [(action, _hm(m.group(2), m.group(3)))] if valid(action) else None
        m = RANGE.match(s)
        if m:
            name = m.group(1)
            on, off = f"включи {name}", f"выключи {name}"
            if valid(on) and valid(off):
                return [(on, _hm(m.group(2), m.group(3))), (off, _hm(m.group(4), m.group(5)))]
    except ValueError:
        return None
    return None


def due(rules, now):
    """Правила, которые срабатывают в эту минуту и ещё не сработали сегодня. Меняет rule['last']."""
    t = time.localtime(now)
    hm, today = time.strftime("%H:%M", t), time.strftime("%Y-%m-%d", t)
    out = []
    for r in rules:
        if r.get("at") == hm and r.get("last") != today:
            r["last"] = today
            out.append(r)
    return out
