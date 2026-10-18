"""Свои фразы-команды: «когда я пишу „работаю“, делай …». Шаги разделяются «;»."""
import re

MAX_PHRASES = 20
MAX_SAY, MAX_DO = 60, 300


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
