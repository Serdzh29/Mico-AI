"""Очистка диска (бета). Удаляет только временные файлы пользователя старше суток и только после «да».
Никогда не трогает системные папки, файлы моложе суток и папки кроме %TEMP%. Отчёт о размерах — только чтение."""
import os, re, tempfile

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


FO_DELETE = 3                 # SHFileOperation: удаление
FOF_ALLOWUNDO = 0x0040        # отправить в корзину, а не стереть навсегда — можно вернуть
FOF_NOCONFIRMATION = 0x0010   # подтверждение уже получено в самом Mico AI
FOF_SILENT = 0x0004
FOF_NOERRORUI = 0x0400


def to_recycle_bin(path):
    """Отправляет файл в корзину Windows — его можно вернуть. True — получилось."""
    try:
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                        ("pTo", wintypes.LPCWSTR), ("fFlags", wintypes.WORD),
                        ("fAnyOperationsAborted", wintypes.BOOL), ("hNameMappings", ctypes.c_void_p),
                        ("lpszProgressTitle", wintypes.LPCWSTR)]
        op = SHFILEOPSTRUCTW()
        op.wFunc = FO_DELETE
        op.pFrom = os.path.abspath(path) + "\0"          # путь заканчивается двумя нулями
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0 and not op.fAnyOperationsAborted
    except (AttributeError, OSError, ImportError):
        return False                                       # не Windows или корзина недоступна — ничего не стираем


def delete_files(files, send=None):
    """Отправляет файлы в корзину, возвращает (отправлено, освобождено байт, пропущено).
    Занятые файлы и всё, что корзина не приняла, пропускаем: навсегда ничего не стираем.
    send — отправка одного файла (по умолчанию — корзина Windows)."""
    send = send or to_recycle_bin
    done, freed, skipped = 0, 0, 0
    for p, size in files:
        if send(p):
            done += 1
            freed += size
        else:
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
