"""Поиск по файлам: агентный инструмент находит по именам, ничего не читая и не меняя.
Проверяется поведение на настоящих временных папках — без Windows и без сети."""
import os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from win import filefind


def make_tree():
    base = tempfile.mkdtemp()
    os.makedirs(os.path.join(base, "Документы", "работа"))
    os.makedirs(os.path.join(base, "Загрузки", "node_modules", "пакет"))
    open(os.path.join(base, "Документы", "отчёт_за_январь.docx"), "w").close()
    open(os.path.join(base, "Документы", "работа", "отчёт_февраль.docx"), "w").close()
    open(os.path.join(base, "Документы", "рецепт_борща.txt"), "w").close()
    open(os.path.join(base, "Загрузки", "установочный_файл.exe"), "w").close()
    open(os.path.join(base, "Загрузки", "node_modules", "пакет", "отчёт_мусор.js"), "w").close()
    return base


def test_match_finds_word_forms_in_names():
    assert filefind.match("отчёт_за_январь.docx", "отчёт") > 0
    assert filefind.match("отчёт_за_январь.docx", "январский отчёт") > 0, "формы слов прощаем"
    assert filefind.match("рецепт_борща.txt", "принтер") == 0.0


def test_search_ranks_and_limits():
    base = make_tree()
    hits = filefind.search([base], "отчёт")
    names = [os.path.basename(p) for p, _ in hits]
    assert "отчёт_за_январь.docx" in names and "отчёт_февраль.docx" in names
    assert "отчёт_мусор.js" not in names, "node_modules не обыскиваем"
    assert all(s >= hits[0][1] for _p, s in hits), "лучшие совпадения впереди"


def test_search_does_not_read_file_contents():
    base = make_tree()
    path = os.path.join(base, "Документы", "секрет.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("очень_секретное_слово")
    hits = filefind.search([base], "очень_секретное_слово")
    assert hits == [], "ищем только по именам, содержимое не читаем"


def test_limits_are_sane():
    assert filefind.MAX_RESULTS <= 50 and filefind.MAX_DEPTH <= 8


def test_format_hits_is_human():
    text = filefind.format_hits([], "кот")
    assert "Ничего не нашёл" in text and "кот" in text
    text = filefind.format_hits([(os.path.join("C:", "Документы", "кот.txt"), 1.0)], "кот")
    assert "кот.txt" in text and "Нашёл" in text


if __name__ == "__main__":
    for n, fn in sorted(list(globals().items())):
        if n.startswith("test_") and callable(fn):
            fn()
            print("OK", n)
    print("ALL OK filefind")
