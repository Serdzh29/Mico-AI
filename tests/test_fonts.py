"""Единый шрифт Mico: Inter лежит с программой, его задают все стили и пузырь. Проверки без Qt."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import theme


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def test_font_files_ship_with_the_app():
    for name in theme.FONT_FILES:
        path = os.path.join(ROOT, "assets", "fonts", name)
        check(os.path.exists(path) and os.path.getsize(path) > 100_000, name)
    check(os.path.exists(os.path.join(ROOT, "assets", "fonts", "LICENSE-Inter.txt")), "лицензия шрифта рядом")


def test_every_stylesheet_sets_the_same_family():
    check(theme.FONT_QSS.count(theme.FONT_FAMILY) == 1 and "font-family" in theme.FONT_QSS, "общий кусок стиля")
    for dark in (True, False):
        check(theme.FONT_QSS in theme.panel_qss("#ffcfa3", dark), f"чат, dark={dark}")
        check(theme.FONT_QSS in theme.app_qss(dark), f"приложение, dark={dark}")
    for dark in (True, False):
        check(theme.FONT_QSS in theme.settings_qss("#ffcfa3", dark), f"настройки, dark={dark}")


def test_no_other_family_hardcoded():
    for name in ("main.py", "blob.py", "theme.py", "installer.py"):
        for m in re.findall(r'font-family:\s*"?([^";]+)', read(name)):
            check(m.strip().strip('"') in (theme.FONT_FAMILY, "{FONT_FAMILY}"), f"{name}: {m}")
    blob = read("blob.py")
    check('QFont("Segoe UI", ' not in blob, "пузырь не использует свой шрифт")
    check("theme.FONT_FAMILY" in blob, "пузырь берёт единый шрифт")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
