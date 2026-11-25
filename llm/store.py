"""Хранение единственной текстовой модели Mico: скачивание GGUF, список и удаление.
Модели лежат в %APPDATA%\\Mico\\models. Файл пишется во временный .part и переименовывается, когда скачан целиком,
поэтому обрыв связи не оставляет испорченную модель под настоящим именем."""
import os

from llm import catalog as model_catalog

# requests грузим только при скачивании модели


def __getattr__(name):
    """Ленивая загрузка requests: модуль доступен и как model_store.requests (на него подменяют запросы в тестах)."""
    if name == "requests":
        import requests
        globals()["requests"] = requests
        return requests
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def models_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "Mico", "models")
    os.makedirs(path, exist_ok=True)
    return path


def path_for(model_id, root=None):
    entry = model_catalog.by_id(model_id)
    if entry is None:
        return None
    return os.path.join(root or models_dir(), entry["file"])


def installed_ids(root=None):
    """Какие текстовые модели из каталога уже скачаны полностью."""
    out = []
    for m in model_catalog.CATALOG:
        p = path_for(m["id"], root)
        if not (p and os.path.isfile(p)):
            continue
        out.append(m["id"])
    return out


def _download_file(url, final, progress, size_hint, retries, timeout):
    """Качает один файл в final через .part, с докачкой. True — файл на месте."""
    import requests
    if os.path.isfile(final):
        if progress:                                   # уже скачан: сообщаем, что он весь на месте
            size = os.path.getsize(final)
            progress(size, size)
        return True
    part = final + ".part"
    for _ in range(retries):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
                if r.status_code not in (200, 206):
                    return False
                if r.status_code == 200 and have:          # сервер не понял Range — начинаем заново
                    have = 0
                try:                                       # сервер мог прислать мусор в Content-Length
                    total = have + int(r.headers.get("Content-Length", 0) or 0)
                except (TypeError, ValueError):
                    total = 0
                mode = "ab" if have else "wb"
                done = have
                if progress:                                  # сразу показываем «0 из N МБ», не ждём первого куска
                    progress(done, total or int(size_hint))
                with open(part, mode) as f:
                    for chunk in r.iter_content(chunk_size=1024 * 64):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        if progress:
                            progress(done, total or int(size_hint))
            os.replace(part, final)
            return True
        except requests.RequestException:
            continue
    return False


def download(model_id, progress=None, root=None, retries=3, timeout=30):
    """Скачивает GGUF. При обрыве загрузку можно продолжить повторным запуском."""
    entry = model_catalog.by_id(model_id)
    if entry is None:
        return False
    hint = int(entry["size_gb"] * 1024 ** 3)
    return _download_file(model_catalog.url(entry), path_for(model_id, root), progress,
                          hint, retries, timeout)


def delete(model_id, root=None):
    """Удаляет модель (и проектор) и недокачанные хвосты. True — удалены или их и не было."""
    p = path_for(model_id, root)
    if p is None:
        return False
    files = [p, p + ".part"]
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError:
            return False
    return True
