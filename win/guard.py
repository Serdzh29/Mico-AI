"""Что Mico не ищет, не показывает и не продаёт.

Чистая логика, без Qt и Windows. Запрос проверяется до поиска и ответа модели,
ответ модели — до показа пользователю.
"""
import re

REFUSALS = {
    "violence": "Про насилие я не ищу и не рассказываю.",
    "sexual": "Материалы сексуального характера я не ищу и не показываю.",
    "drugs": "Запрещённые вещества я не ищу и не объясняю.",
    "age": "Продвигать и продавать товары с возрастными ограничениями я не буду.",
    "buy": "Покупки цифровых товаров через Mico недоступны, и магазин приложений я не открываю.",
    "profanity": "Ищу и отвечаю без ненормативной лексики. Переформулируй, пожалуйста, без мата.",
}
REPLY_BLOCKED = "Об этом я не могу рассказать. Давай о чём-нибудь другом 🙂"

VIOLENCE = re.compile(r"\b(убий\w*|убить|убью|расчлен\w*|пытк\w*|изнасил\w*|избиени\w*|расстрел\w*|резн[яи]|"
                      r"расправ\w*|murder\w*|torture\w*|gore)\b", re.I)
# «убей процесс», «kill task» — обычные команды Windows, их не блокируем
PC_CONTEXT = re.compile(r"процесс|задач|программ|приложени|служб|\bprocess|\btask", re.I)
SEXUAL = re.compile(r"порно\w*|porn\w*|эротик\w*|хентай|hentai|nsfw|onlyfans|\bnudes?\b|"
                    r"голы[ехй]\s+(женщин|девушк|девочк|мальчик|парн|мужчин)|"
                    r"секс\w*\s+(видео|фото|картин|материал|контент|сцен)|интим\w*\s+(фото|видео)|18\+", re.I)
DRUGS = re.compile(r"наркот\w*|героин\w*|кокаин\w*|амфетамин\w*|мефедрон\w*|метамфетамин\w*|экстази\b|"
                   r"марихуан\w*|гашиш\w*|конопл\w*|фентанил\w*|\bcocaine\b|\bheroin\b|\bfentanyl\b|\bmdma\b|\blsd\b|лсд\b",
                   re.I)
AGE_GOODS = re.compile(r"алкогол\w*|водк\w*|\bвин[оаеуы]\b|\bпив[оаеуо]\w*|сигарет\w*|вейп\w*|табак\w*|кальян\w*|"
                       r"казино|букмекер\w*|ставк\w*\s+на|азартн\w*|лотере\w*|снюс\w*|энергетик\w*", re.I)
SALE = re.compile(r"купи\w*|продай|продат\w*|продаж\w*|продв\w*|реклам\w*|промо\w*|скидк\w*|заказ\w*|оптом|"
                  r"продаю|где\s+(купить|взять)", re.I)
BUY = re.compile(r"(купи\w*|покуп\w*|оплат\w*|оплач\w*|подписк\w*|донат\w*|заплат\w*)\s.{0,40}?"
                 r"(в\s+приложени\w*|внутри\s+приложени\w*|в\s+магазин\w*|приложени\w*|игр\w*|скин\w*|подписк\w*|"
                 r"премиум|дополнени\w*|внутриигров\w*|валют\w*|алмаз\w*|монет\w*|in-app)|"
                 r"in-app|внутриигров\w*\s+покуп\w*|"
                 r"(открой|запусти|покажи)\s+магазин\w*|магазин\w*\s+(приложени\w*|windows|microsoft|майкрософт)|"
                 r"ms-windows-store|microsoft\.com/store|apps\.microsoft\.com", re.I)
PROFANITY = re.compile(r"(?<![а-яёa-z])(хуй|хуе|хуё|хуя|хуи|пизд|ебан|ебат|ёбан|ёбат|ебл[аоиуыеё]|еба[лнт]|"
                       r"бляд|блядь|блять|бля(?![а-яё])|сук[аи]|сучк|мудак|мудил|гандон|залуп|пидор|пидар|"
                       r"долбоеб|fuck|shit|bitch)[а-яёa-z]*", re.I)


def _norm(text):
    return (text or "").lower().replace("ё", "е")


def request_refusal(text):
    """Отказ, если запрос про запрещённое; иначе None. Мат в обычной фразе не блокирует — см. search_refusal."""
    t = _norm(text)
    if SEXUAL.search(t):
        return REFUSALS["sexual"]
    if VIOLENCE.search(t) and not PC_CONTEXT.search(t):
        return REFUSALS["violence"]
    if DRUGS.search(t):
        return REFUSALS["drugs"]
    if AGE_GOODS.search(t) and SALE.search(t):
        return REFUSALS["age"]
    if BUY.search(t):
        return REFUSALS["buy"]
    return None


def search_refusal(text):
    """Для поиска в интернете: всё из request_refusal плюс ненормативная лексика."""
    return request_refusal(text) or (REFUSALS["profanity"] if PROFANITY.search(text or "") else None)


def _mask(m):
    w = m.group(0)
    return w[0] + "*" * (len(w) - 1)


def reply_guard(text):
    """Ответ модели перед показом: запрещённое заменяем, мат маскируем."""
    t = text or ""
    tl = _norm(t)
    if SEXUAL.search(tl) or DRUGS.search(tl) or (VIOLENCE.search(tl) and not PC_CONTEXT.search(tl)):
        return REPLY_BLOCKED
    if AGE_GOODS.search(tl) and SALE.search(tl):
        return REPLY_BLOCKED
    return PROFANITY.sub(_mask, t)
