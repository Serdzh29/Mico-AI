"""Свои фразы-команды: «когда я пишу „работаю“, делай …». Шаги разделяются «;»."""
import re

MAX_PHRASES = 20
MAX_SAY, MAX_DO = 60, 300

# «когда я пишу „работаю“, делай открой блокнот» — добавление своей фразы прямо в чате
ADD = re.compile(r"^когда я пишу\s+[«\"']?(?P<say>[^»\"',:]{1,60})[»\"']?\s*[:,]?\s*делай\s+(?P<do>.+)$", re.I)


def parse_add(ql):
    """«когда я пишу …, делай …» → (say, do) или None, если это не добавление фразы."""
    m = ADD.match(" ".join((ql or "").split()))
    if not m:
        return None
    say, do = m.group("say").strip(), m.group("do").strip()
    return (say, do) if valid(say, do) else None


def norm(text):
    return " ".join(re.sub(r"[^\w\s]", " ", (text or "").lower().replace("ё", "е")).split())


def valid(say, do):
    say, do = (say or "").strip(), (do or "").strip()
    return bool(say and do) and len(say) <= MAX_SAY and len(do) <= MAX_DO


def steps(do):
    return [s.strip() for s in do.split(";") if s.strip()]


def find(ql, phrases):
    """Шаги для фразы, если она совпала с одной из своих; иначе None."""
    key = norm(ql)
    for p in phrases or []:
        if norm(p.get("say")) == key:
            return steps(p.get("do", ""))
    return None
