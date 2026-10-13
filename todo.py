"""Список дел (бета): «добавь в список дел X», «покажи список дел», «отметь X выполненным».
Хранится зашифрованно вместе с остальными данными (таблица todos в storage)."""
import re

ADD = re.compile(r"^(?:добавь|запиши)\s+в\s+список\s+дел[:\s]+(.+)$")
SHOW = re.compile(r"^(?:покажи|какие\s+у\s+меня\s+есть)\s+(?:мои\s+)?(?:список\s+дел|дела)$|^мои\s+дела$")
DONE = re.compile(r"^отметь\s+(.+?)\s+(?:выполненн\w*|сделанн\w*|готов\w*)$")
CLEAR = re.compile(r"^(?:очисти|удали)\s+выполненные\s+дела$")


def command(ql):
    s = (ql or "").strip(" .!?")
    if CLEAR.match(s):
        return ("clear", None)
    if SHOW.match(s):
        return ("show", None)
    m = DONE.match(s)
    if m:
        return ("done", m.group(1).strip())
    m = ADD.match(s)
    if m:
        return ("add", m.group(1).strip())
    return None


def render(items):
    if not items:
        return "Список дел пуст."
    lines = []
    for i, (_id, text, done) in enumerate(items, 1):
        mark = "✔" if done else "○"
        lines.append(f"{mark} {text}")
    return "\n".join(lines)


def find_open(items, query):
    """Открытое дело, в котором есть запрос (без учёта регистра). None, если нет или совпадений больше одного."""
    q = query.lower()
    hits = [it for it in items if not it[2] and q in it[1].lower()]
    return hits[0] if len(hits) == 1 else None
