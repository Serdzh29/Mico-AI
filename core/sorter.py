"""Порядок в «Загрузках» (бета): раскладывает файлы верхнего уровня по папкам по типу.
Сначала показывает план, переносит только после «да». Перенос можно отменить."""
import os, re, shutil

CATEGORIES = {
    "Изображения": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".svg"},
    "Документы": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".md"},
    "Архивы": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Установщики": {".exe", ".msi"},
    "Видео": {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "Музыка": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
}
PHRASE = re.compile(r"^(?:наведи\s+порядок\s+в\s+загрузках|разложи\s+загрузки)$")
UNDO = re.compile(r"^отмени\s+(?:сортировку|порядок\s+в\s+загрузках)$")


def command(ql):
    s = (ql or "").strip(" .!?")
    if PHRASE.match(s):
        return "sort"
    if UNDO.match(s):
        return "undo"
    return None


def category(name):
    ext = os.path.splitext(name)[1].lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return None


def plan(folder):
    """[(откуда, куда)] для файлов верхнего уровня, которые подходят под категорию. Скрытые файлы пропускаем."""
    out = []
    try:
        names = os.listdir(folder)
    except OSError:
        return out
    for name in sorted(names):
        src = os.path.join(folder, name)
        if name.startswith(".") or not os.path.isfile(src):
            continue
        cat = category(name)
        if not cat:
            continue
        target_dir = os.path.join(folder, cat)
        dst = os.path.join(target_dir, name)
        base, ext = os.path.splitext(name)
        n = 2
        while os.path.exists(dst):             # не перезаписываем: добавляем номер
            dst = os.path.join(target_dir, f"{base} ({n}){ext}")
            n += 1
        out.append((src, dst))
    return out


def apply(moves):
    """Переносит файлы. Возвращает список реально перенесённых пар (для отмены) и число пропущенных."""
    done, skipped = [], 0
    for src, dst in moves:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            done.append((src, dst))
        except OSError:
            skipped += 1                       # файл занят или нет доступа — не трогаем
    return done, skipped


def undo(done):
    """Возвращает файлы на места. Возвращает число возвращённых."""
    back = 0
    for src, dst in reversed(done):
        try:
            if os.path.exists(dst) and not os.path.exists(src):
                shutil.move(dst, src)
                back += 1
        except OSError:
            continue
    return back
