"""Ответ на вопросы о создателе Mico AI: «кто тебя создал?», «кто твой создатель?», «кто тебя придумал?» и похожие."""
import re

CREATOR = "Serdzh Kozhe"

_WHO = re.compile(r"\b(кто|кем|чей|чья|чьё|чьи)\b")
_MAKE = re.compile(r"\b(созда\w*|придума\w*|сделал\w*|сделан\w*|разработ\w*|написа\w*|автор\w*|создател\w*|"
                   r"родител\w*|программист\w*|изобрел\w*|изобрёл\w*)\b")
_NOT_ABOUT = re.compile(r"книг|песн|фильм|музык|сериал|стат(ь|ью|ьи)|игр[аеыу]?\b|картин|фото")
_ABOUT_MICO = re.compile(r"\b(ты|тебя|тебе|тобой|твой|твоя|твоё|твое|твои|тебе|мико|mico)\b")


def answer(q):
    """Reply с ответом, если вопрос о создателе Mico. Иначе None (вопрос обрабатывают дальше)."""
    from actions import Reply
    low = (q or "").lower().replace("ё", "е")
    if _NOT_ABOUT.search(low):                       # «кто твой любимый автор книги» — не про Mico AI
        return None
    if not (_WHO.search(low) and _MAKE.search(low) and _ABOUT_MICO.search(low)):
        return None
    return Reply(f"Меня создал {CREATOR} 💛", "happy")       # тёплый ответ о создателе — всегда с радостью
