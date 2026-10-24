"""Голос Mico AI — чистая логика, без Qt и без звука: очистка текста для речи, деление на фразы,
громкость по времени (для рта), конец речи пользователя. Всё проверяется тестами."""
import re

import numpy as np

SENT_END = re.compile(r"(?<=[.!?…])\s+|\n+")
_CODE = re.compile(r"```.*?```", re.S)
_URL = re.compile(r"https?://\S+|www\.\S+")
_MARK = re.compile(r"[*_#`>|~]+")
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]+")
_TAG = re.compile(r"^\s*\[\w+\]\s*")          # служебная метка настроения в начале ответа


def clean_for_speech(text):
    """Убирает то, что нельзя читать вслух: код, ссылки, разметку, эмодзи, метки настроения."""
    text = _TAG.sub("", text or "")
    text = _CODE.sub(" ", text)
    text = _URL.sub(" ", text)
    text = _EMOJI.sub(" ", text)
    text = _MARK.sub(" ", text)
    return " ".join(text.split())


def split_sentences(text, max_len=220):
    """Фразы для синтеза по одной: так Mico начинает говорить раньше, чем готов весь ответ."""
    out = []
    for part in SENT_END.split(clean_for_speech(text)):
        part = part.strip()
        while len(part) > max_len:
            cut = part.rfind(" ", 0, max_len)
            if cut < max_len // 2:
                cut = max_len
            out.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            out.append(part)
    return out


def envelope(samples, sr, frame_ms=20):
    """Громкость по кадрам, значения 0..1. По ней рот открывается в такт речи."""
    x = np.asarray(samples, dtype=np.float32).ravel()
    n = max(1, int(sr * frame_ms / 1000))
    frames = len(x) // n
    if frames == 0:
        return np.zeros(0, dtype=np.float32)
    rms = np.sqrt((x[: frames * n].reshape(frames, n) ** 2).mean(axis=1))
    ref = max(float(np.percentile(rms, 95)), 1e-4)          # громкость относительно самой громкой части фразы
    return np.clip(rms / ref, 0.0, 1.0).astype(np.float32)


def level_at(env, t, frame_ms=20):
    """Громкость в момент t (секунды от начала фразы)."""
    if env is None or len(env) == 0 or t < 0:
        return 0.0
    i = int(t * 1000 / frame_ms)
    return float(env[min(i, len(env) - 1)])


def mouth_for_level(level):
    """Форма рта по громкости: (полуширина, высота) в долях радиуса Mico. Тихо — закрыт, громко — открыт."""
    level = max(0.0, min(1.0, level))
    return (0.10 + 0.09 * level, 0.02 + 0.12 * level)


def trailing_silence_ms(samples, sr, thresh=0.012, frame_ms=30):
    """Сколько миллисекунд тишины в конце записи. Нужно, чтобы понять, что человек закончил фразу."""
    x = np.asarray(samples, dtype=np.float32).ravel()
    n = max(1, int(sr * frame_ms / 1000))
    frames = len(x) // n
    if frames == 0:
        return 0
    rms = np.sqrt((x[: frames * n].reshape(frames, n) ** 2).mean(axis=1))
    quiet = 0
    for v in rms[::-1]:
        if v >= thresh:
            break
        quiet += 1
    return quiet * frame_ms


def frame_rms(samples, sr, frame_ms=30):
    x = np.asarray(samples, dtype=np.float32).ravel()
    n = max(1, int(sr * frame_ms / 1000))
    frames = len(x) // n
    if frames == 0:
        return np.zeros(0, dtype=np.float32)
    return np.sqrt((x[: frames * n].reshape(frames, n) ** 2).mean(axis=1))


def adaptive_thresh(samples, sr, sens=1.0):
    """Порог речи по фону: тихий микрофон и шумная комната работают одинаково.
    Фон — 20-й перцентиль уровня; речь заметно громче фона. sens > 1 — чувствительнее."""
    rms = frame_rms(samples, sr)
    if len(rms) == 0:
        return 0.004
    floor = float(np.percentile(rms, 20))
    return max(0.002, min(0.08, floor * 3.0 + 0.002)) / max(0.2, float(sens))


def has_speech(samples, sr, thresh=0.012, min_ms=250):
    """Была ли вообще речь в записи: короткие щелчки и тишину не отправляем в распознавание."""
    x = np.asarray(samples, dtype=np.float32).ravel()
    n = max(1, int(sr * 0.03))
    frames = len(x) // n
    if frames == 0:
        return False
    rms = np.sqrt((x[: frames * n].reshape(frames, n) ** 2).mean(axis=1))
    return int((rms >= thresh).sum()) * 30 >= min_ms


# ----- выразительность речи -----
# Настроение → (длительность, разброс, разброс длительности) для Piper.
# Больше length_scale — медленнее. Больше noise_scale — живее и «теплее», но хуже стабильность.
PROSODY = {
    "idle":      (1.00, 0.667, 0.80),
    "happy":     (0.93, 0.78, 0.90),
    "love":      (0.98, 0.75, 0.90),
    "proud":     (0.96, 0.72, 0.85),
    "playful":   (0.92, 0.85, 1.00),
    "excited":   (0.88, 0.85, 1.00),
    "laugh":     (0.90, 0.90, 1.00),
    "curious":   (1.02, 0.70, 0.85),
    "thinking":  (1.08, 0.60, 0.75),
    "surprised": (0.90, 0.85, 1.00),
    "scared":    (1.12, 0.90, 1.00),
    "sad":       (1.18, 0.55, 0.70),
    "worried":   (1.08, 0.70, 0.85),
    "angry":     (0.95, 0.90, 1.00),
    "shy":       (1.10, 0.60, 0.75),
    "confused":  (1.05, 0.75, 0.90),
    "sleepy":    (1.25, 0.50, 0.60),
}


def prosody(mood):
    return PROSODY.get(mood, PROSODY["idle"])


def pause_after(sentence):
    """Пауза после фразы в секундах: вопрос и восклицание звучат с паузой, многоточие — с долгой."""
    s = (sentence or "").rstrip()
    if s.endswith(("...", "…")):
        return 0.5
    if s.endswith("?"):
        return 0.35
    if s.endswith("!"):
        return 0.3
    if s.endswith("."):
        return 0.25
    if s.endswith((",", ";", ":", "—")):          # короткая пауза перед продолжением фразы: речь не скомкана
        return 0.2
    return 0.15


# ----- пробуждение «мико» -----
WAKE_WORDS = {"мико", "mico", "miko", "мыко", "майко", "мика", "мико"}   # варианты, которые Whisper пишет для «Mico»
WAKE_SCAN_WORDS = 6                    # имя ищем в начале фразы, а не в середине разговора


def wake_word_list(raw):
    """Слова из настройки «Слова пробуждения» («мико, mico») → множество в нижнем регистре."""
    words = {w.strip().lower() for w in re.split(r"[,;\s]+", raw or "") if w.strip()}
    return words or set(WAKE_WORDS)


_STOP_CORE = ("хватит", "хватит пожалуйста", "всё хватит", "все хватит",
              "переключись на текст", "переключись на текстовый чат", "переключись в текст", "текстовый режим")
_STOP_WRAP = re.compile(r"^(?:(?:мико|mico|ну|да|ладно|ок|окей|всё|все)\s+)*")
_STOP_TAIL = re.compile(r"(?:\s+(?:мико|mico|спасибо|пока|ладно|всё|все|давай))*$")


def is_stop_phrase(text):
    """Фраза «хватит» (с обращением или «спасибо» и т. п.) — закончить голосовой чат. Только целая фраза:
    «хватит ли памяти» или «хватит смотреть» голосовой чат не закрывают."""
    t = re.sub(r"[^\w\s]", " ", (text or "").lower().replace("ё", "е"))
    t = re.sub(r"\s+", " ", t).strip()
    t = _STOP_WRAP.sub("", t)
    t = _STOP_TAIL.sub("", t).strip()
    return t in _STOP_CORE


def after_wake(text, words=None):
    """Если фраза начинается с имени — возвращает то, что сказано после него (может быть «»). Иначе None.
    «микрофон» и «микро» не совпадают: сравниваем целые слова."""
    names = words or WAKE_WORDS
    for idx, m in enumerate(re.finditer(r"[^\W_]+", text or "")):
        if idx >= WAKE_SCAN_WORDS:
            break
        if m.group(0).lower() in names:
            return (text[m.end():]).strip(" ,.!?;:—-")
    return None


def tune(mood, cfg):
    """Все настройки голоса из вкладки «Голос» → параметры синтеза и громкость.
    length/noise/noise_w — для Piper; pause — множитель пауз; volume — громкость (1.0 = 100%)."""
    cfg = cfg or {}
    mood = mood if (cfg.get("voice_mood", True) and mood) else "idle"
    length, noise, noise_w = prosody(mood)
    speed = max(0.5, min(2.0, float(cfg.get("voice_speed", 1.0))))
    expr = max(0.0, min(1.0, float(cfg.get("voice_expr", 60)) / 100.0))
    length = length / speed                           # скорость: больше — быстрее
    noise = noise * (0.5 + expr)                      # выразительность: больше — живее
    noise_w = noise_w * (0.5 + expr)
    pause = max(0.0, min(2.0, float(cfg.get("voice_pause", 1.0))))
    volume = max(0.0, min(1.5, float(cfg.get("voice_volume", 100)) / 100.0))
    return {"mood": mood, "length": length, "noise": min(noise, 1.2), "noise_w": min(noise_w, 1.3),
            "pause": pause, "volume": volume, "speed": speed, "expr": expr}
