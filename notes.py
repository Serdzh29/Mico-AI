"""Быстрые заметки: «запиши: купить молоко», «что я записывал сегодня». Хранятся зашифрованно в Store."""
import re, time

ADD = re.compile(r"^(?:запиши|заметка|запомни заметку|запомни)\s*[:,]\s*(?P<a>.+)$|^(?:запиши|заметка|запомни заметку)\s+(?P<b>.+)$")
LIST = re.compile(r"^(что я записывал|мои заметки|покажи заметки|заметки)(\s+сегодня)?\??$")
SEARCH = re.compile(r"^(?:найди|поищи|поиск|найти)\s+(?:в\s+)?(?:заметк\w*|записях)\s*[:,]?\s*(?P<a>.+)$"
                    r"|^(?:заметки|записи|что я записывал)\s+(?:о|про|об|обо|по)\s+(?P<b>.+?)\??$")


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
    m = SEARCH.match(s)
    if m:
        query = (m.group("a") or m.group("b") or "").strip()
        if query:
            return "search", query[:200]
    return None


def _same_word(stem, word):
    """Слова совпадают, если у них общее начало не короче 4 букв и почти вся длина более короткого:
    «встрече» ↔ «встреча», «молоко» ↔ «молоку»; «дом» ↔ «дома» не совпадает (слишком коротко)."""
    p = 0
    for a, b in zip(stem, word):
        if a != b:
            break
        p += 1
    return p >= 4 and p >= min(len(stem), len(word)) - 2


def search(query, items, limit=10):
    """Заметки, в которых встречаются все слова запроса (с учётом окончаний: «молоко» найдёт «молоку»).
    Если такой нет, берём заметки, где совпало хотя бы одно слово. Новые — выше."""
    import knowledge
    qstems = [knowledge._stem(t) for t in knowledge._terms(query)]
    if not qstems:
        return []
    scored = []
    for it in items:
        words = knowledge._terms(it["text"])
        hit = sum(1 for st in qstems if any(_same_word(st, w) for w in words))
        if hit:
            scored.append((hit, it["ts"], it))
    if not scored:
        return []
    best = max(h for h, _, _ in scored)
    full = [x for x in scored if x[0] == len(qstems)]
    pool = full if full else [x for x in scored if x[0] == best]
    pool.sort(key=lambda x: -x[1])
    return [it for _, _, it in pool[:limit]]


def format_search(query, items):
    if not items:
        return f"По запросу «{query}» заметок не нашёл."
    lines = [f"{time.strftime('%d.%m %H:%M', time.localtime(i['ts']))} — {i['text']}" for i in items]
    return f"Нашёл заметки по запросу «{query}»:\n" + "\n".join(lines)


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
