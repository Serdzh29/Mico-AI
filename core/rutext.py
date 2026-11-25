"""Нормализация русского текста: «десять минут» -> «10 минут», числа словами -> цифрами, транслитерация."""
import re

_UNITS = {"ноль": 0, "нуль": 0, "один": 1, "одна": 1, "одну": 1, "два": 2, "две": 2, "три": 3, "четыре": 4,
          "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9}
_TEENS = {"десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14,
          "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19}
_TENS = {"двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
         "восемьдесят": 80, "девяносто": 90}
_HUNDS = {"сто": 100, "двести": 200, "триста": 300, "четыреста": 400, "пятьсот": 500, "шестьсот": 600,
          "семьсот": 700, "восемьсот": 800, "девятьсот": 900}

# слово -> (значение, ранг). Ранг нужен, чтобы «двадцать пять» склеить в 25, а «семь тридцать» (время) — нет.
NUM = {}
for _d, _r in ((_UNITS, 1), (_TEENS, 2), (_TENS, 3), (_HUNDS, 4)):
    for _w, _v in _d.items():
        NUM[_w] = (_v, _r)
NUM["ноль"] = NUM["нуль"] = (0, 0)


def _can_follow(prev, nxt):
    return (prev == 4 and nxt in (1, 2, 3)) or (prev == 3 and nxt == 1)


def words_to_digits(text):
    toks, out, i = text.split(), [], 0
    while i < len(toks):
        w = toks[i].strip(",.!?;:")
        info = NUM.get(w)
        if not info:
            out.append(toks[i])
            i += 1
            continue
        total, rank = info
        i += 1
        while i < len(toks):
            nxt = NUM.get(toks[i].strip(",.!?;:"))
            if not nxt or toks[i - 1].endswith(",") or not _can_follow(rank, nxt[1]):
                break
            total, rank = total + nxt[0], nxt[1]
            i += 1
        out.append(str(total))
    return " ".join(out)


def normalize(text):
    """Нижний регистр, ё->е, «полчаса» -> «30 минут», «на час» -> «на 1 час», числа словами -> цифры."""
    t = text.lower().replace("ё", "е").strip()
    t = re.sub(r"\bпол\s?часа\b", "30 минут", t)
    t = re.sub(r"\bполтора\s+часа\b", "90 минут", t)
    t = re.sub(r"\bполминуты\b", "30 секунд", t)
    t = re.sub(r"\bчетверть\s+часа\b", "15 минут", t)
    t = words_to_digits(t)
    t = re.sub(r"\b(на|через|за)\s+(час|минуту|минутку|секунду)\b", lambda m: f"{m.group(1)} 1 {m.group(2)}", t)
    return re.sub(r"\s+", " ", t)


_TR = dict(zip("абвгдезийклмнопрстуфхц", "abvgdezijklmnoprstufhc"))
_TR.update({"ё": "e", "ж": "zh", "ч": "ch", "ш": "sh", "щ": "sch", "ы": "y", "э": "e", "ю": "yu", "я": "ya",
            "ъ": "", "ь": ""})


def translit(text):
    """Грубая транслитерация, чтобы сопоставить «дискорд» с Discord."""
    return "".join(_TR.get(c, c) for c in text.lower())
