"""Вопрос «что на экране?»: снимок экрана для облачной модели с картинкой (Groq).
Снимок живёт только в памяти и уходит в запрос; на диск он не пишется. Чистые функции здесь, захват — в capture_jpeg()."""
import base64, io, re

MAX_SIDE = 1280                  # длинная сторона: текст на экране ещё читается, а запрос не раздувается
MAX_BYTES = 1_500_000            # Groq принимает картинку в base64 до 4 МБ; берём с запасом
QUALITY = (80, 65, 50)           # если картинка всё ещё велика — сжимаем сильнее

# «что на экране?», «что у меня на экране сейчас», «что написано на моём экране», «опиши экран»
QUESTION = re.compile(
    r"\bчто\b[^?.!]{0,40}?\bна\s+(?:[а-яё]+\s+){0,1}?экран"
    r"|\b(?:опиши|посмотри|глянь|взгляни|прочитай|скажи)\b[^?.!]{0,30}?\bэкран",
    re.IGNORECASE)


def is_question(q):
    """Спрашивают про то, что сейчас на экране. Длинные фразы с «экран» внутри — не про снимок."""
    s = " ".join((q or "").lower().replace("ё", "е").split())
    if not s or len(s) > 90:
        return False
    return bool(QUESTION.search(s.replace("ё", "е")))


def prompt_text(question, mood_rule=""):
    """Текст вопроса для модели с картинкой. Инструкции — в тексте, а не в роли system: так надёжнее для vision-моделей."""
    return ("Тебе прислали снимок экрана пользователя. Ответь на вопрос по тому, что реально видно на снимке. "
            "Если чего-то не видно или текст не читается, так и скажи, не угадывай. "
            "Пароли, номера карт, коды и личные данные не выписывай: можно сказать, что они есть на экране. "
            "Отвечай по-русски, коротко и по делу. "
            f"Вопрос: {' '.join(str(question).split())[:300]}"
            + ((" " + mood_rule.strip()) if mood_rule else ""))


def data_url(jpeg):
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")


def encode_jpeg(image):
    """PIL-изображение → JPEG-байты не больше MAX_BYTES, если это возможно. Исходник не меняется."""
    img = image.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    data = b""
    for quality in QUALITY:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) <= MAX_BYTES:
            break
    return data


def capture_jpeg():
    """Снимок всех мониторов в JPEG (только в памяти). Работает только на Windows с mss и Pillow."""
    import mss
    from PIL import Image
    with mss.mss() as s:
        shot = s.grab(s.monitors[0])
    image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    return encode_jpeg(image)
