"""Поиск в интернете с коротким ответом, как у поисковика: «найди в интернете рецепт борща», «какие новости сегодня».

Порядок работы:
1. Выдача DuckDuckGo: заголовки, адреса и короткие описания (ключ и платная модель не нужны).
2. Текст первых двух страниц выдачи — чтобы ответ опирался не только на короткие описания.
3. Модель пишет 2–4 предложения по сути вопроса и ссылается на источники номерами [1], [2].
4. Если модель не ответила, показываем первое описание из выдачи — ответ всё равно есть.
Сеть передаётся снаружи (параметры fetch), поэтому тесты работают без интернета.
Включается настройкой web_search_on (проверяется в brain.py)."""
import html, re
import urllib.parse

from web import find as webfind

LIMIT = 5                    # результатов выдачи, которые показываем модели и в источниках
EXCERPT_PAGES = 2            # сколько страниц открываем за текстом
EXCERPT_LEN = 1200           # символов текста с каждой страницы
SNIPPET_LEN = 240

# Прямые просьбы поискать в интернете. «загугли», «в гугле», «яндекс» обслуживает webfind (он открывает браузер)
_INTERNET = re.compile(r"\b(?:в интернете|в сети|онлайн)\b")
_BROWSER_WORDS = re.compile(r"загугли|погугли|гугли|гугл|google|яндекс", re.IGNORECASE)
_NEWS = re.compile(r"^(?:какие\s+|что\s+)?(?:сейчас\s+|сегодня\s+)?(?:новости|последние новости|что нового)\b")
_VERBS = re.compile(r"\b(?:найди|поищи|поищите|посмотри|проверь|узнай|расскажи|объясни|скажи)\b")
_SNIPPET = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)
_DROP_BLOCKS = re.compile(r"<(script|style|noscript|svg|head)\b.*?</\1>", re.S | re.I)


def request(text):
    """Фраза → {'query', 'question'} или None, если это не просьба искать в интернете."""
    s = " ".join(str(text or "").lower().replace("ё", "е").split()).strip(" .!?")
    if not s or _BROWSER_WORDS.search(s):
        return None
    if _NEWS.match(s):
        return {"query": "новости сегодня", "question": s}
    if not _INTERNET.search(s):
        return None
    query = _VERBS.sub(" ", s)
    query = _INTERNET.sub(" ", query)
    query = re.sub(r"\b(?:мне|пожалуйста|про|о|об|насчет|по)\b", " ", query)
    query = " ".join(query.split()).strip(" ,.:;!?")
    if not query:
        return None
    return {"query": query[:200], "question": s[:300]}


def _clean(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).split())


def parse_results(page, limit=LIMIT):
    """Страница выдачи → [{'title', 'url', 'host', 'snippet'}] в порядке выдачи."""
    out = []
    for chunk in re.split(r'<div class="result[ "]', page or "")[1:]:
        hit = webfind.parse_ddg(chunk, limit=1)
        if not hit:
            continue
        title, url = hit[0]
        m = _SNIPPET.search(chunk)
        host = urllib.parse.urlsplit(url).netloc
        out.append({"title": title, "url": url, "host": host[4:] if host.startswith("www.") else host,
                    "snippet": _clean(m.group(1))[:SNIPPET_LEN] if m else ""})
        if len(out) >= limit:
            break
    return out


def search(query, fetch=webfind._fetch):
    """Результаты поиска. None — не удалось связаться с поиском (пустая страница); [] — ничего не нашлось."""
    page = fetch(webfind.ddg_url(query))
    if not page:
        return None
    return parse_results(page)


def page_text(page, limit=EXCERPT_LEN):
    """Видимый текст страницы: без скриптов, стилей и разметки. Пустая строка, если текста почти нет."""
    text = _DROP_BLOCKS.sub(" ", page or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())[:limit]


def excerpts(results, fetch=webfind._fetch, count=EXCERPT_PAGES):
    """Текст первых страниц выдачи → [(номер источника, текст)]. Недоступные страницы пропускаем."""
    out = []
    for i, r in enumerate(results[:count], 1):
        text = page_text(fetch(r["url"]))
        if len(text) > 200:                                      # совсем короткий текст пользы не даёт
            out.append((i, text))
    return out


def answer_prompt(question, results, pages=()):
    """Запрос к модели: короткий ответ по выдаче и текстам страниц, со ссылками на номера источников."""
    by_no = dict(pages)
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']} ({r['host']}): {r['snippet'] or 'описания нет'}")
        if i in by_no:
            lines.append(f"    Текст страницы: {by_no[i]}")
    return ("Ты отвечаешь как краткий ответ поисковика: по-русски, 2–4 коротких предложения, сразу по сути вопроса, "
            "без вступлений. Опирайся только на результаты поиска ниже и ссылайся на них номерами в квадратных "
            "скобках, например [1]. Если в результатах нет ответа, так и скажи, не придумывай. "
            f"Вопрос: {question}\nРезультаты поиска:\n" + "\n".join(lines))


def fallback_text(results):
    """Ответ, если модель не ответила: первое описание из выдачи. Пусто, если выдача пустая."""
    if not results:
        return ""
    first = results[0]
    return f"Модель сейчас не ответила. Вот что нашлось: {first['snippet'] or first['title']} [1]"


def sources_text(results):
    return "Источники:\n" + "\n".join(f"[{i}] {r['url']}" for i, r in enumerate(results, 1))
