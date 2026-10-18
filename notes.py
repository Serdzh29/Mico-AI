"""Быстрые заметки: «запиши: купить молоко», «что я записывал сегодня». Хранятся зашифрованно в Store."""
import re, time

ADD = re.compile(r"^(?:запиши|заметка|запомни заметку|запомни)\s*[:,]\s*(?P<a>.+)$|^(?:запиши|заметка|запомни заметку)\s+(?P<b>.+)$")
LIST = re.compile(r"^(что я записывал|мои заметки|покажи заметки|заметки)(\s+сегодня)?\??$")


def parse(ql):
    """('add', текст) | ('list', 'today'|'all') | None."""
    s = " ".join(ql.lower().replace("ё", "е").split())
    m = ADD.match(s)
    if m:
        text = (m.group("a") or m.group("b") or "").strip()            # текст из того варианта, что совпал
        if text:
            return "add", text[:500]
    m = LIST.match(s)
    if m:
        return "list", "today" if m.group(2) else "all"
    return None


def _day_start(ts):
    lt = time.localtime(ts)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def format_list(items, scope, now=None):
    now = now or time.time()
    if scope == "today":
        start = _day_start(now)
        items = [i for i in items if i["ts"] >= start]
    if not items:
        return "Заметок за сегодня нет." if scope == "today" else "Заметок пока нет."
    lines = [f"{time.strftime('%d.%m %H:%M', time.localtime(i['ts']))} — {i['text']}" for i in items[-20:]]
    return "Заметки:\n" + "\n".join(lines)
