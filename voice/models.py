"""Каталог голосов и модели: где лежат, как проверить и как скачать один раз. После этого Mico работает офлайн.
Синтез речи: Piper (русские голоса в .onnx; лицензию каждого голоса смотри в его MODEL_CARD) и Edge TTS (облачные голоса Microsoft).
Распознавание — Whisper. Скачивание только по явному выбору голоса."""
import hashlib
import os
import urllib.request

from data.storage import APPDIR

VOICES_DIR = os.path.join(APPDIR, "voices")
WHISPER_DIR = os.path.join(VOICES_DIR, "whisper")
WHISPER_MODEL = "small"
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU"

# Каталог голосов: файл модели и её sha256 (конфиг .onnx.json докачивается рядом, без проверки хеша).
# Piper — локальные голоса (работают без интернета)
PIPER_VOICES = {
    "irina":  {"title": "Лира", "file": "ru_RU-irina-medium.onnx",
               "sha256": "8ff38212d23da300bbe3705c645e6e5b9475f0bfde01558eb17813e22acaaaaa", "gender": "ж"},
    "ruslan": {"title": "Рико", "file": "ru_RU-ruslan-medium.onnx",
               "sha256": "72a5f88e0b20928064eb45d88e1daa21f8af62d18613580d32cbb4aed48dcf7f", "gender": "м"},
}

# Edge TTS — облачные голоса Microsoft (требует интернет, не требует загрузки)
EDGE_VOICES = {
    "dmitry": {"title": "Дмитрий (Edge)", "voice_name": "ru-RU-DmitryNeural", "gender": "м", "lang": "ru"},
    "svetlana": {"title": "Светлана (Edge)", "voice_name": "ru-RU-SvetlanaNeural", "gender": "ж", "lang": "ru"},
    "dariya": {"title": "Дарья (Edge)", "voice_name": "ru-RU-DariyaNeural", "gender": "ж", "lang": "ru"},
    "jenny": {"title": "Jenny (Edge)", "voice_name": "en-US-JennyNeural", "gender": "ж", "lang": "en"},
    "guy": {"title": "Guy (Edge)", "voice_name": "en-US-GuyNeural", "gender": "м", "lang": "en"},
    "aria": {"title": "Aria (Edge)", "voice_name": "en-US-AriaNeural", "gender": "ж", "lang": "en"},
}

# Объединённый каталог всех голосов
VOICES = {**PIPER_VOICES, **EDGE_VOICES}

DEFAULT_VOICE = "irina"
VOICE_TITLES = {k: v["title"] for k, v in VOICES.items()}     # уникальные имена голосов Mico AI


def is_edge_voice(name):
    """Проверяет, является ли голос облачным Edge TTS."""
    return name in EDGE_VOICES


def get_edge_voice_name(name):
    """Возвращает voice_name для Edge TTS (например 'ru-RU-DmitryNeural')."""
    if name in EDGE_VOICES:
        return EDGE_VOICES[name]["voice_name"]
    return None


def _voice_dir():
    return os.path.join(VOICES_DIR, "piper")


def paths(name):
    """Piper: (модель .onnx, конфиг .onnx.json). Для Edge TTS возвращает (None, None)."""
    if name in EDGE_VOICES:
        return None, None
    if name not in PIPER_VOICES:
        return None, None
    base = os.path.join(_voice_dir(), PIPER_VOICES[name]["file"])
    return base, base + ".json"


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def is_installed(name):
    """Голос готов: файлы на месте и хеш модели совпадает. Edge TTS голоса всегда 'установлены' (не требуют загрузки)."""
    if name in EDGE_VOICES:
        return True  # Edge TTS не требует загрузки
    if name not in PIPER_VOICES:
        return False
    model, conf = paths(name)
    if not model or not conf:
        return False
    if not os.path.isfile(model) or not os.path.isfile(conf):
        return False
    return sha256_file(model) == PIPER_VOICES[name]["sha256"]


def _fetch(url, dest, progress=None):
    tmp = dest + ".part"
    with urllib.request.urlopen(url, timeout=30) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            block = r.read(1 << 16)
            if not block:
                break
            f.write(block)
            done += len(block)
            if progress and total:
                progress(done / total)
    return tmp


def download(name, progress=None):
    """Скачивает голос во временные файлы, проверяет хеш и только потом кладёт на место.
    Бросает исключение при ошибке сети или хеша. Edge TTS голоса не требуют загрузки."""
    if name in EDGE_VOICES:
        return None, None  # Edge TTS не требует загрузки
    if name not in PIPER_VOICES:
        raise ValueError(f"неизвестный голос: {name}")
    os.makedirs(_voice_dir(), exist_ok=True)
    model, conf = paths(name)
    tmp = _fetch(f"{PIPER_BASE}/{name}/medium/{PIPER_VOICES[name]['file']}", model, progress)
    if sha256_file(tmp) != PIPER_VOICES[name]["sha256"]:
        os.remove(tmp)
        raise ValueError("контрольная сумма голоса не совпала — файл повреждён или подменён")
    os.replace(tmp, model)
    tmp_conf = _fetch(f"{PIPER_BASE}/{name}/medium/{PIPER_VOICES[name]['file']}.json", conf, progress)
    os.replace(tmp_conf, conf)
    return model, conf


