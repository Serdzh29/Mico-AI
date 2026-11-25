"""Название чата: берём первый запрос пользователя и коротко его записываем.
Чистая логика без Qt и без модели: модель здесь не нужна, поэтому в названии не попадают её рассуждения."""
import re

MAX_WORDS = 5          # сколько слов запроса оставляем
MAX_CHARS = 40         # длина названия в боковом меню
DEFAULT = "Новый чат"

# слова-обращения и вежливые начала, которые не несут темы
_FILLER_RE = re.compile(r"^(мико|mico|пожалуйста|подскажи|подскажите|скажи|скажите|слушай|привет|ну|эй)[,!.\s]+",
                        re.IGNORECASE)


def make_title(text):
    """Короткое название по первому запросу: 2–5 слов, с заглавной буквы, с многоточием, если обрезали."""
    full = " ".join(str(text or "").split())
    s = full
    while True:
        cut = _FILLER_RE.sub("", s, count=1)
        if cut == s or not cut.strip():
            break
        s = cut
    s = s.strip(" .,!?:;«»\"'`") or full.strip(" .,!?:;«»\"'`")
    if not s:
        return DEFAULT
    out = ""
    for word in s.split()[:MAX_WORDS]:
        cand = (out + " " + word).strip()
        if len(cand) > MAX_CHARS:
            break
        out = cand
    if not out:                                   # одно очень длинное слово
        out = s[:MAX_CHARS]
    truncated = len(out) < len(s)
    return out[0].upper() + out[1:] + ("…" if truncated else "")
