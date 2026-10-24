"""Хранение моделей встроенного режима: скачивание с Hugging Face (с докачкой), список, удаление.
Модели лежат в %APPDATA%\\Mico\\models. Файл пишется во временный .part и переименовывается, когда скачан целиком,
поэтому обрыв связи не оставляет испорченную модель под настоящим именем.
У модели для экрана есть ещё один файл — «проектор» картинки (mmproj); без него экран не понимается."""
import os

import requests

import model_catalog


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


def mmproj_path_for(model_id, root=None):
    """Файл-проектор картинки для модели для экрана; None — у модели его нет."""
    entry = model_catalog.by_id(model_id)
    if entry is None or not entry.get("mmproj_file"):
        return None
    return os.path.join(root or models_dir(), entry["mmproj_file"])


def installed_ids(root=None):
    """Какие модели из каталога уже скачаны полностью (для экрана — вместе с проектором)."""
    out = []
    for m in model_catalog.CATALOG:
        p = path_for(m["id"], root)
        if not (p and os.path.isfile(p)):
            continue
        mp = mmproj_path_for(m["id"], root)
        if mp and not os.path.isfile(mp):
            continue
        out.append(m["id"])
    return out


def _download_file(url, final, progress, size_hint, retries, timeout):
    """Качает один файл в final через .part, с докачкой. True — файл на месте."""
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
                total = have + int(r.headers.get("Content-Length", 0) or 0)
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
    """Скачивает модель (и проектор, если нужен). progress(скачано_байт, всего_байт) — по всем файлам вместе:
    основной файл и проектор. Раньше проектор качался молча, и полоска вставала на 99%.
    True — все файлы на месте. False — не получилось; можно нажать «Скачать» ещё раз, докачка продолжится."""
    entry = model_catalog.by_id(model_id)
    if entry is None:
        return False
    main_hint = int(entry["size_gb"] * 1024 ** 3)
    mm_name = entry.get("mmproj_file")
    mm_hint = int(entry.get("mmproj_size_gb", 1) * 1024 ** 3) if mm_name else 0
    # файл → [скачано, всего]; до ответа сервера «всего» берём из каталога
    parts = {"main": [0, main_hint], "mm": [0, mm_hint]}

    def emit():
        if progress:
            done = parts["main"][0] + parts["mm"][0]
            total = parts["main"][1] + parts["mm"][1]
            progress(min(done, total), total)

    def tracker(name):
        def on_bytes(done, total):
            parts[name] = [done, total or parts[name][1]]
            emit()
        return on_bytes if progress else None

    emit()
    ok = _download_file(model_catalog.url(entry), path_for(model_id, root), tracker("main"),
                        main_hint, retries, timeout)
    if not ok or not mm_name:
        return ok
    mmproj_url = f"{model_catalog.HF}/{entry['repo']}/resolve/main/{mm_name}"
    return _download_file(mmproj_url, mmproj_path_for(model_id, root), tracker("mm"),
                          mm_hint, retries, timeout)


def delete(model_id, root=None):
    """Удаляет модель (и проектор) и недокачанные хвосты. True — удалены или их и не было."""
    p = path_for(model_id, root)
    if p is None:
        return False
    files = [p, p + ".part"]
    mp = mmproj_path_for(model_id, root)
    if mp:
        files += [mp, mp + ".part"]
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError:
            return False
    return True
