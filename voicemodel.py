"""Голосовая модель Vosk: скачивание с сайта разработчика, распаковка, проверка и установка вручную.

Каждая ошибка объясняется по-человечески: нет сети, адрес не найден, истекло время, нет места на диске,
файл повреждён. Чистые функции здесь тестируются локально (без интернета)."""
import os
import shutil
import socket
import ssl
import tempfile
import urllib.error
import urllib.request
import zipfile

MODEL_NAME = "vosk-model-small-ru-0.22"
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
MODEL_SIZE_MB = 45                        # примерно, для проверки места на диске
CHUNK = 64 * 1024

# Каталог русских моделей. Чем больше модель, тем точнее распознавание и тем больше памяти и места она займёт.
MODELS = {
    "vosk-model-small-ru-0.22": {
        "title": "Быстрая и лёгкая (по умолчанию)", "size_mb": 45,
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"},
    "vosk-model-ru-0.22": {
        "title": "Точнее: распознаёт лучше, медленнее", "size_mb": 1500,
        "url": "https://alphacephei.com/vosk/models/vosk-model-ru-0.22.zip"},
    "vosk-model-ru-0.42": {
        "title": "Самая точная: нужно больше памяти", "size_mb": 1800,
        "url": "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"},
}
DEFAULT_MODEL = MODEL_NAME


def model_name_of(name):
    """Имя модели из каталога; неизвестное или пустое — модель по умолчанию."""
    return name if name in MODELS else DEFAULT_MODEL


def model_url(name=MODEL_NAME):
    return MODELS[model_name_of(name)]["url"]


def model_size_mb(name=MODEL_NAME):
    return MODELS[model_name_of(name)]["size_mb"]


def is_installed(path):
    """Модель на месте: в папке есть акустическая модель и граф (это то, что нужно распознаванию)."""
    return bool(path) and os.path.isfile(os.path.join(path, "am", "final.mdl")) and \
        os.path.isdir(os.path.join(path, "graph"))


def default_dir(root, name=MODEL_NAME):
    return os.path.join(root, "models", model_name_of(name))


def installed_names(root):
    """Какие модели из каталога уже лежат на диске (для подписей в настройках)."""
    return [n for n in MODELS if is_installed(default_dir(root, n))]


def free_mb(folder):
    os.makedirs(folder, exist_ok=True)
    return shutil.disk_usage(folder).free // (1024 * 1024)


def explain(exc):
    """Понятная причина ошибки: что случилось и что сделать."""
    if isinstance(exc, urllib.error.HTTPError):
        return (f"сервер alphacephei.com ответил «{exc.code} {exc.reason}». "
                + ("адрес модели не найден — возможно, сайт поменял файл" if exc.code == 404
                   else "сервер временно недоступен, попробуй позже" if exc.code >= 500
                   else "сервер отказал в загрузке"))
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, ssl.SSLError):
            return "не удалось установить защищённое соединение (сертификат или прокси мешает)"
        if isinstance(reason, socket.gaierror):
            return "нет соединения с alphacephei.com: не открывается адрес (проверь интернет и DNS)"
        return f"нет соединения с alphacephei.com ({reason}). Проверь интернет, VPN и файрвол"
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return "сайт не ответил вовремя. Проверь интернет и попробуй ещё раз"
    if isinstance(exc, zipfile.BadZipFile):
        return "скачанный файл повреждён (не архив). Попробуй скачать снова или выбери файл вручную"
    if isinstance(exc, OSError) and getattr(exc, "errno", None) == 28:
        return "не хватает места на диске"
    return f"неизвестная ошибка: {exc.__class__.__name__}: {exc}"


def fetch(url, dest_zip, progress=None, timeout=20, opener=urllib.request.urlopen):
    """Скачивает файл во временный .part и переименовывает, только когда он полный.
    progress(скачано_байт, всего_байт_или_None). Возвращает dest_zip или выбрасывает исключение."""
    part = dest_zip + ".part"
    with opener(url, timeout=timeout) as resp:
        total = resp.headers.get("Content-Length")
        total = int(total) if total and total.isdigit() else None
        if total and free_mb(os.path.dirname(dest_zip) or ".") < total // (1024 * 1024) * 2:
            raise OSError(28, "no space")
        done = 0
        with open(part, "wb") as f:
            while True:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        if total and done != total:
            os.remove(part)
            raise urllib.error.ContentTooShortError(f"получено {done} из {total} байт", None)
    os.replace(part, dest_zip)
    return dest_zip


def unpack(zip_path, root, name=MODEL_NAME):
    """Распаковывает архив модели в root. Возвращает путь к модели или выбрасывает BadZipFile.
    Архив может содержать папку модели сверху или файлы в корне — понимаем оба варианта."""
    target = default_dir(root, name)
    tmp = tempfile.mkdtemp(prefix="vosk_", dir=root)
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        entries = os.listdir(tmp)
        src = os.path.join(tmp, entries[0]) if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])) else tmp
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.move(src, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def fetch_model(root, url=None, progress=None, opener=urllib.request.urlopen, name=MODEL_NAME):
    """Полная установка выбранной модели: скачать → распаковать → проверить.
    Возвращает (True, путь) или (False, причина)."""
    name = model_name_of(name)
    url = url or model_url(name)
    if is_installed(default_dir(root, name)):
        return True, default_dir(root, name)
    need = model_size_mb(name) * 2 + 200            # архив + распакованная модель + запас
    try:
        if free_mb(root) < need:
            return False, f"не хватает места на диске: нужно около {need} МБ, свободно {free_mb(root)} МБ"
        zip_path = os.path.join(root, name + ".zip")
        fetch(url, zip_path, progress=progress, opener=opener)
        path = unpack(zip_path, root, name)
        os.remove(zip_path)
    except Exception as e:
        return False, explain(e)
    if not is_installed(path):
        return False, "модель распакована, но не нашлась нужная структура (am/final.mdl, graph). Выбери файл вручную"
    return True, path


def install_from_file(user_path, root):
    """Ручная установка: архив модели или папка с моделью. Возвращает (True, путь) или (False, причина)."""
    if os.path.isdir(user_path):
        if not is_installed(user_path):
            return False, "в папке нет модели: нужны am/final.mdl и папка graph"
        target = default_dir(root)
        if os.path.abspath(user_path) != os.path.abspath(target):
            if os.path.isdir(target):
                shutil.rmtree(target)
            shutil.copytree(user_path, target)
        return True, target
    if user_path.lower().endswith(".zip") and os.path.isfile(user_path):
        try:
            path = unpack(user_path, root)
        except zipfile.BadZipFile:
            return False, explain(zipfile.BadZipFile())
        except OSError as e:
            return False, explain(e)
        if not is_installed(path):
            return False, "в архиве нет модели: нужны am/final.mdl и папка graph"
        return True, path
    return False, "выбери архив модели (.zip) или папку, где лежит модель"
