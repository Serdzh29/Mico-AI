"""Поиск по своим файлам: агентный инструмент Mico AI с подтверждением «да».
Ищем ТОЛЬКО по именам файлов и папок в личных папках пользователя (Документы, Рабочий стол,
Загрузки, Картинки). Содержимое файлов не читаем и ничего не меняем — поиск ничего не ломает.
Чистая логика сравнения имён — проверяется в tests/test_filefind.py без Windows."""
import os
import re

MAX_RESULTS = 20            # не засыпаем чат длинным списком
MAX_DEPTH = 4               # глубоко не копаем: важное лежит ближе
SKIP_DIRS = {"appdata", "node_modules", "__pycache__", ".git", "$recycle.bin", "temp", "cache"}
# имена личных папок: английские и русские (Windows называет их по-разному)
ROOT_NAMES = ("Documents", "Desktop", "Downloads", "Pictures", "Music", "Videos",
              "Документы", "Рабочий стол", "Загрузки", "Изображения", "Музыка", "Видео")


def norm(s):
    return str(s or "").lower().replace("ё", "е")


def stems(query):
    """Слова запроса длиной от 3 букв: по ним сравниваем имена."""
    return [w for w in re.findall(r"[а-яa-z0-9]+", norm(query)) if len(w) >= 3]


def match(name, query):
    """0..1: насколько имя файла подходит под запрос. Формы слов и регистр прощаем."""
    n = norm(name)
    words = stems(query)
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in n)          # «отчёт» находит «отчёт_за_январь»
    return hits / len(words)


def user_roots(home=None):
    """Папки, где личные файлы пользователя. Несуществующие пропускаем."""
    home = home or os.path.expanduser("~")
    return [os.path.join(home, name) for name in ROOT_NAMES if os.path.isdir(os.path.join(home, name))]


def search(roots, query, limit=MAX_RESULTS):
    """Идёт по папкам и возвращает [(путь, оценка)] по убыванию подходящести, максимум limit штук."""
    hits = []
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            rel = os.path.relpath(dirpath, root)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth >= MAX_DEPTH:
                dirnames[:] = []                     # глубже MAX_DEPTH не копаем
            dirnames[:] = [d for d in dirnames if norm(d) not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames:
                s = match(name, query)
                if s > 0:
                    hits.append((os.path.join(dirpath, name), s))
    hits.sort(key=lambda h: (-h[1], h[0]))
    return hits[:limit]


def format_hits(hits, query=""):
    """Готовый ответ человеку: списком, с понятной просьбой уточнить, если пусто."""
    if not hits:
        return f"Ничего не нашёл по запросу «{query}» в твоих папках. Попробуй другое слово из имени файла."
    lines = [f"Нашёл по запросу «{query}»:"]
    for path, _s in hits:
        folder = os.path.dirname(path)
        name = os.path.basename(path)
        short = os.path.basename(folder)
        lines.append(f"• {name}  —  {short}")
    return "\n".join(lines)
