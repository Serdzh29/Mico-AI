"""Удалённые функции не должны вернуться: перевод текста, поиск файлов и программ, индекс компьютера.
История версий (version.py, CHANGELOG.md, BACKLOG.md) — это записи о прошлом, их не проверяем."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = {"version.py", "CHANGELOG.md", "BACKLOG.md"}
BANNED = [
    r"Ctrl\+Alt\+T", r"переведи\s+буфер", r"Перевести буфер", r"гугл переводчик", r"translate_selection",
    r"def translate\b", r"hk_tr\b", r"Найти файл", r"find_files", r"\"find_file\"", r"def find_file\b",
    r"indexer", r"проиндексируй", r"найди телеграм", r"Индекс компьютера", r"## Индекс",
    r"index_on", r"replace_index", r"load_index", r"on_index_text", r"index_text", r"status_lbl",
    r"_idx\b", r"start_index", r"index_records",
]
found = []
for root, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", ".github", "tests")]   # тесты сами перечисляют запрещённое
    for name in files:
        if name in HISTORY or not name.endswith((".py", ".md", ".txt")):
            continue
        path = os.path.join(root, name)
        text = open(path, encoding="utf-8", errors="replace").read()
        for pat in BANNED:
            if re.search(pat, text):
                found.append((os.path.relpath(path, ROOT), pat))
assert not found, found
assert not os.path.exists(os.path.join(ROOT, "indexer.py"))
assert not os.path.exists(os.path.join(ROOT, "tests", "test_index.py"))

if __name__ == "__main__":
    print("OK test_no_removed_features")
