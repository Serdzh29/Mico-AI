"""Файлы, которые перетащили на Mico (WI). Читаем только текст и картинки; больше 60 КБ текста не берём."""
import os

TEXT_EXT = {".txt", ".md", ".log", ".csv", ".json", ".xml", ".html", ".htm", ".py", ".js", ".ts", ".ini",
            ".cfg", ".yaml", ".yml", ".ps1", ".bat", ".reg", ".srt", ".sql", ".java", ".cs", ".cpp", ".c", ".h"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
MAX_BYTES = 60 * 1024


def kind(path):
    """'text' | 'image' | 'unsupported'."""
    ext = os.path.splitext(str(path or ""))[1].lower()
    if ext in TEXT_EXT:
        return "text"
    if ext in IMAGE_EXT:
        return "image"
    return "unsupported"


def read_text(path):
    """Текст файла (до MAX_BYTES). Сначала UTF-8, потом Windows-1251. Ошибка чтения — пустая строка."""
    try:
        with open(path, "rb") as f:
            raw = f.read(MAX_BYTES)
    except OSError:
        return ""
    for enc in ("utf-8", "cp1251"):
        try:
            return raw.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").strip()
