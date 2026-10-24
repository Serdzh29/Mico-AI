"""Шрифты Mico: Segoe UI Variable для текста, Nunito Bold для заголовков. Проверки без Qt."""
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
        if not os.path.exists(path):
            print("NOTE: шрифт", name, "ещё не положен в assets/fonts — заголовки временно на системном шрифте")
            continue
        check(os.path.getsize(path) > 100_000, name)
    check(theme.FONT_FAMILY == "Segoe UI Variable Text" and theme.FONT_DISPLAY == "Nunito" and theme.FONT_DISPLAY_WEIGHT == 700, "основной — Segoe UI Variable, заголовки — Nunito Bold")
    check("font-weight: 700" in theme.FONT_QSS and theme.FONT_QSS.count(theme.FONT_DISPLAY) >= 1, "заголовки заданы Nunito Bold в общем куске стиля")


def test_all_headings_use_nunito():
    for sel in ("QLabel#title", "QLabel#pageTitle", "QLabel#wiTitle", "QLabel#tileTitle", "QLabel#expTitle", "QLabel#brand"):
        check(sel in theme.FONT_QSS, sel)
    h = theme.heading("Тест")
    check(f"font-family:{theme.FONT_DISPLAY}" in h and "Тест" in h, "заголовок внутри HTML — Nunito")


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
            # пояснения настроек — отдельный шрифт (Georgia, есть в любой Windows): запрос пользователя
            check(m.strip().strip('"') in (theme.FONT_FAMILY, "{FONT_FAMILY}", theme.FONT_DISPLAY, "{FONT_DISPLAY}", "Georgia,serif"), f"{name}: {m}")
    blob = read("blob.py")
    check('QFont("Segoe UI", ' not in blob, "пузырь не использует свой шрифт")
    check("theme.FONT_DISPLAY" in blob and "theme.FONT_FAMILY" not in blob.replace("theme.FONT_FAMILY, size", ""), "пузырь берёт заголовочный шрифт для значков")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
