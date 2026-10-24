"""База знаний Mico AI: короткие статьи из папки knowledge/*.md. Поиск по словам (с транслитерацией),
ответ со ссылкой на раздел. Ответ даётся без обращения к модели, если статья подходит."""
import os, re, sys

from ru_text import translit

STOP = set("как что такое это почему где какой какая какие мне мой моя мои можно нужно сделать сделай "
           "пожалуйста подскажи расскажи объясни есть ли или для при без на в во с по к о об из".split())
MIN_SCORE = 3
# общие слова: по ним нельзя выбрать статью («режим» сам по себе не значит «режим тишины»)
GENERIC = set("режим режима режиме работает работать делает функция функции зачем почему ли значит означает "
              "настройка настройки включить выключить включу выключу использовать пользоваться программа".split())


def _base():
    return getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))


def load(folder=None):
    """Все статьи: [{'title', 'body', 'source'}]. Разделы — заголовки «## ». Файлы — из knowledge/."""
    folder = folder or os.path.join(_base(), "knowledge")
    items = []
    if not os.path.isdir(folder):
        return items
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md"):
            continue
        text = open(os.path.join(folder, name), encoding="utf-8").read()
        source = name[:-3]
        for part in re.split(r"\n(?=## )", text):
            part = part.strip()
            if not part.startswith("## "):
                continue
            title, _, body = part[3:].partition("\n")
            items.append({"title": title.strip(), "body": body.strip(), "source": source})
    return items


def _terms(text):
    words = re.findall(r"[а-яёa-z0-9]+", text.lower().replace("ё", "е"))
    return [w for w in words if w not in STOP and len(w) > 1]


def _stem(word):
    """Грубая основа слова: «переключить» и «переключение» сходятся по первым 7 буквам."""
    return word[:7] if len(word) >= 7 else word


def search(query, items, limit=1):
    """Лучшие статьи по запросу. Возвращает список (score, статья); пусто, если ничего подходящего."""
    qterms = set(_terms(query)) - GENERIC
    if not qterms:
        return []
    qvariants = {t: {_stem(t), _stem(translit(t))} for t in qterms}
    scored = []
    for it in items:
        title_words = _terms(it["title"])
        body_words = _terms(it["body"])
        score = 0
        title_hit = False
        for t, stems in qvariants.items():
            if any(w.startswith(s) for w in title_words for s in stems if s):
                score += 4
                title_hit = True
            elif any(w.startswith(s) for w in body_words for s in stems if s):
                score += 1
        # совпадение только в тексте статьи («дела» в тексте про .NET) — не ответ: нужен заголовок
        if score >= MIN_SCORE and title_hit:
            scored.append((score, it))
    scored.sort(key=lambda x: -x[0])
    return scored[:limit]


def answer(query, items):
    """Текст ответа из базы знаний или None."""
    hits = search(query, items)
    if not hits:
        return None
    _, it = hits[0]
    body = it["body"]
    if len(body) > 700:
        body = body[:700].rsplit(" ", 1)[0] + "…"
    src = {"mico": "справка Mico AI", "windows": "справка Windows", "components": "справка о компонентах Windows"}.get(it["source"], it["source"])
    return f"{it['title']}\n\n{body}\n\n(источник: {src})"
