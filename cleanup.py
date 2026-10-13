"""Очистка диска (бета). Удаляет только временные файлы пользователя старше суток и только после «да».
Никогда не трогает системные папки, файлы моложе суток и папки кроме %TEMP%. Отчёт о размерах — только чтение."""
import os, re, tempfile, time

PHRASE_SIZE = re.compile(r"^(?:что\s+занимает\s+место(?:\s+на\s+диске)?|где\s+место\s+на\s+диске)$")
PHRASE_CLEAN = re.compile(r"^очисти\s+(?:временные\s+файлы|временные\s+файлы\s+ПК|временные\s+файлы\s+windows)$")
MIN_AGE = 24 * 3600


def command(ql):
    s = (ql or "").strip(" .!?")
    if PHRASE_SIZE.match(s):
        return "size"
    if PHRASE_CLEAN.match(s):
        return "clean"
    return None


def temp_dir():
    return tempfile.gettempdir()


def old_temp_files(folder, now, min_age=MIN_AGE):
    """[(путь, размер)] для файлов в folder старше min_age. Подпапки не трогаем: только файлы верхнего уровня."""
    out = []
    try:
        names = os.listdir(folder)
    except OSError:
        return out
    for name in names:
        p = os.path.join(folder, name)
        try:
            if os.path.isfile(p) and now - os.path.getmtime(p) >= min_age:
                out.append((p, os.path.getsize(p)))
        except OSError:
            continue
    return out


def delete_files(files):
    """Удаляет файлы, возвращает (удалено, освобождено байт, пропущено). Занятые файлы пропускаем."""
    done, freed, skipped = 0, 0, 0
    for p, size in files:
        try:
            os.remove(p)
            done += 1
            freed += size
        except OSError:
            skipped += 1
    return done, freed, skipped


def _mb(n):
    return f"{n / 1024 ** 2:.1f} МБ"


def size_text(folders):
    """folders: {название: байты}. Самые большие — первыми."""
    if not folders:
        return "Не смог посмотреть размеры папок."
    rows = sorted(folders.items(), key=lambda kv: -kv[1])
    return "Больше всего места занимают:\n" + "\n".join(f"• {name} — {_mb(size)}" for name, size in rows)


def folder_size(path, limit_files=50000):
    """Размер папки целиком (с подпапками), с ограничением на число файлов, чтобы не зависнуть."""
    total, n = 0, 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            n += 1
            if n > limit_files:
                return total
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                continue
    return total
