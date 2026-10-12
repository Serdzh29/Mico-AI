"""Память диалога о последнем действии. Позволяет понимать короткие продолжения:
«переключи трек» → «дальше» (ещё раз), «громче» → «ещё» (ещё громче), «выключи блютуз» → «назад» (вернуть),
«выключи вайфай» → «а блютуз?» (то же действие для другой функции)."""
import re, time

TTL = 300                       # сек: дольше этого «дальше» уже не относится к прошлому действию
_last = {}

REPEAT_WORDS = {"дальше", "ещё", "еще", "ещё раз", "еще раз", "давай ещё", "давай еще", "продолжай",
                "снова", "опять", "ещё немного", "еще немного", "больше", "следующий", "давай дальше"}
UNDO_WORDS = {"назад", "обратно", "верни назад", "верни как было", "отмени", "отмени это",
              "отмени последнее", "отмени действие"}


def remember(kind, repeat=None, undo=None, **extra):
    """repeat/undo — функции без аргументов, возвращающие Reply (или None)."""
    _last.clear()
    _last.update(kind=kind, repeat=repeat, undo=undo, at=time.time(), **extra)


def last():
    if not _last or time.time() - _last.get("at", 0) > TTL:
        return None
    return dict(_last)


def clear():
    _last.clear()


def bare(ql):
    """'дальше!' → 'дальше'."""
    return " ".join(re.sub(r"[^\w\s]", " ", ql.lower().replace("ё", "е")).split())


def is_repeat(ql):
    return bare(ql).replace("ё", "е") in {w.replace("ё", "е") for w in REPEAT_WORDS}


def is_undo(ql):
    return bare(ql).replace("ё", "е") in {w.replace("ё", "е") for w in UNDO_WORDS}
