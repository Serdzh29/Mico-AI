"""Каталог голосов и модели: где лежат, как проверить и как скачать один раз. После этого Mico работает офлайн.
Синтез речи: Piper (русские голоса в .onnx; лицензию каждого голоса смотри в его MODEL_CARD)
и RHVoice (GPL-3.0; голоса ставятся отдельно, с rhvoice.org, Mico их не скачивает и не распространяет).
Распознавание — Whisper. Скачивание только по явному выбору голоса."""
import hashlib
import os
import shutil
import urllib.request

from storage import APPDIR

VOICES_DIR = os.path.join(APPDIR, "voices")
WHISPER_DIR = os.path.join(VOICES_DIR, "whisper")
WHISPER_MODEL = "small"
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU"

ENGINE_LABEL = {"piper": "Piper", "rhvoice": "RHVoice"}
RHVOICE_SITE = "https://rhvoice.org"
RHVOICE_EXE_NAMES = ["RHVoice-test.exe", "RHVoice-test"]
RHVOICE_DIRS = [r"C:\Program Files\RHVoice", r"C:\Program Files (x86)\RHVoice"]

# Каталог голосов: файл модели и её sha256 (конфиг .onnx.json докачивается рядом, без проверки хеша).
VOICES = {
    "irina":  {"engine": "piper", "title": "Лира",   "file": "ru_RU-irina-medium.onnx",
               "sha256": "8ff38212d23da300bbe3705c645e6e5b9475f0bfde01558eb17813e22acaaaaa", "gender": "ж"},
    "dmitri": {"engine": "piper", "title": "Брин", "file": "ru_RU-dmitri-medium.onnx",
               "sha256": "f073356ebc4bd0f80c5af58df2953a5988bd5bdab1eb38635ce960b071fbefcb", "gender": "м"},
    "denis":  {"engine": "piper", "title": "Кейн",   "file": "ru_RU-denis-medium.onnx",
               "sha256": "15fab56e11a097858ee115545d0f697fc2a316c41a291a5362349fb870411b0a", "gender": "м"},
    "ruslan": {"engine": "piper", "title": "Рико",  "file": "ru_RU-ruslan-medium.onnx",
               "sha256": "72a5f88e0b20928064eb45d88e1daa21f8af62d18613580d32cbb4aed48dcf7f", "gender": "м"},
}
# RHVoice: голоса открытого синтезатора (GPL-3.0). Работают, если RHVoice установлен на компьютере.
VOICES.update({
    "rv_aleksandr": {"engine": "rhvoice", "title": "Александр", "speaker": "aleksandr", "gender": "м"},
    "rv_anna":      {"engine": "rhvoice", "title": "Анна",      "speaker": "anna",      "gender": "ж"},
    "rv_elena":     {"engine": "rhvoice", "title": "Елена",     "speaker": "elena",     "gender": "ж"},
    "rv_irina":     {"engine": "rhvoice", "title": "Ирина",     "speaker": "irina",     "gender": "ж"},
})
DEFAULT_VOICE = "irina"
VOICE_TITLES = {k: v["title"] for k, v in VOICES.items()}     # уникальные имена голосов Mico AI


def engine(name):
    return VOICES[name]["engine"]


def _voice_dir(name):
    return os.path.join(VOICES_DIR, engine(name))


def paths(name):
    """Piper: (модель .onnx, конфиг .onnx.json)."""
    base = os.path.join(_voice_dir(name), VOICES[name]["file"])
    return base, base + ".json"


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def rhvoice_exe():
    """Путь к RHVoice-test, если RHVoice установлен; иначе None."""
    for name in RHVOICE_EXE_NAMES:
        found = shutil.which(name)
        if found:
            return found
    for folder in RHVOICE_DIRS:
        for name in RHVOICE_EXE_NAMES:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    return None


def is_installed(name):
    """Голос готов: файлы на месте и хеш модели совпадает (RHVoice — если установлен RHVoice)."""
    if name not in VOICES:
        return False
    if VOICES[name]["engine"] == "rhvoice":
        return rhvoice_exe() is not None
    model, conf = paths(name)
    if not os.path.isfile(model) or not os.path.isfile(conf):
        return False
    return sha256_file(model) == VOICES[name]["sha256"]


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
    Бросает исключение при ошибке сети или хеша."""
    if name not in VOICES:
        raise ValueError(f"неизвестный голос: {name}")
    if VOICES[name]["engine"] == "rhvoice":
        raise RuntimeError(f"Голос «{VOICE_TITLES[name]}» требует RHVoice. Установите его с {RHVOICE_SITE}")
    os.makedirs(_voice_dir(name), exist_ok=True)
    model, conf = paths(name)
    tmp = _fetch(f"{PIPER_BASE}/{name}/medium/{VOICES[name]['file']}", model, progress)
    if sha256_file(tmp) != VOICES[name]["sha256"]:
        os.remove(tmp)
        raise ValueError("контрольная сумма голоса не совпала — файл повреждён или подменён")
    os.replace(tmp, model)
    tmp_conf = _fetch(f"{PIPER_BASE}/{name}/medium/{VOICES[name]['file']}.json", conf, progress)
    os.replace(tmp_conf, conf)
    return model, conf


def whisper_ready():
    return os.path.isdir(WHISPER_DIR) and any(os.scandir(WHISPER_DIR))
