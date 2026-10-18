"""Файлы, которые перетащили на Mico AI (Mico AI). Читаем только текст и картинки; больше 60 КБ текста не берём."""
import os
import re

TEXT_EXT = {".txt", ".md", ".log", ".csv", ".json", ".xml", ".html", ".htm", ".py", ".js", ".ts", ".ini",
            ".cfg", ".yaml", ".yml", ".ps1", ".bat", ".reg", ".srt", ".sql", ".java", ".cs", ".cpp", ".c", ".h"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
DOC_EXT = {".pdf", ".docx"}              # документы: текст достаём отдельно
MAX_CHARS = 60000
MAX_BYTES = 60 * 1024


def kind(path):
    """'text' | 'image' | 'unsupported'."""
    ext = os.path.splitext(str(path or ""))[1].lower()
    if ext in TEXT_EXT:
        return "text"
    if ext in IMAGE_EXT:
        return "image"
    if ext in DOC_EXT:
        return "text"
    return "unsupported"


def read_text(path):
    """Текст файла. PDF и DOCX разбираем отдельно; остальное — как текст (UTF-8, потом Windows-1251).
    Ошибка чтения — пустая строка."""
    ext = os.path.splitext(str(path or ""))[1].lower()
    if ext == ".pdf":
        return _pdf_text(path)
    if ext == ".docx":
        return _docx_text(path)
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


def _pdf_text(path):
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        out, total = [], 0
        for page in reader.pages:
            t = (page.extract_text() or "").strip()
            if t:
                out.append(t)
                total += len(t)
            if total >= MAX_CHARS:
                break
        return "\n\n".join(out)[:MAX_CHARS].strip()
    except Exception:
        return ""


def _docx_text(path):
    """DOCX — это zip с XML: берём абзацы из word/document.xml, без сторонних библиотек."""
    import zipfile
    import xml.etree.ElementTree as ET
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
    except Exception:
        return ""
    paras = []
    for p in root.iter(W + "p"):
        t = "".join(node.text or "" for node in p.iter(W + "t")).strip()
        if t:
            paras.append(t)
    return "\n\n".join(paras)[:MAX_CHARS].strip()


def excerpt(text, question, limit=6000):
    """Фрагменты документа, где есть слова вопроса, в исходном порядке. Короткий текст — целиком."""
    if len(text) <= limit:
        return text
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    words = re.findall(r"[а-яa-z0-9]+", (question or "").lower().replace("ё", "е"))
    stems = {w[:5] for w in words if len(w) >= 4}          # грубо берём основу: «сроки» ~ «сроков»
    ranked = []
    for i, p in enumerate(paras):
        low = p.lower().replace("ё", "е")
        ranked.append((sum(1 for st in stems if st in low), i, p))
    picked, total = [], 0
    for score, i, p in sorted(ranked, key=lambda r: (-r[0], r[1])):
        if score == 0:
            break
        if total + len(p) + 2 <= limit:
            picked.append((i, p))
            total += len(p) + 2
    if not picked:
        return text[:limit]
    return "\n\n".join(p for _, p in sorted(picked))

