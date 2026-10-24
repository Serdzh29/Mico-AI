"""Мастер установки/удаления следует теме Windows; цвет Mico меняется сразу при выборе. Проверки без Qt."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_installer_follows_windows_theme():
    src = read("installer.py")
    check("def qss(dark=None)" in src and "theme.system_dark()" in src, "палитра выбирается по теме Windows")
    check("_DARK = {" in src and "_LIGHT = {" in src, "есть тёмная и светлая палитры")
    check("setStyleSheet(QSS)" not in src and src.count("setStyleSheet(qss())") == 3, "мастер установки и удаления используют qss()")


def test_onboarding_previews_color_on_mico():
    onb = read("onboarding.py")
    check("on_color=None" in onb and "self.on_color(hex_color)" in onb, "выбор цвета передаётся наружу")
    main = read("main.py")
    check("def recolor(hex_color):" in main and 'cfg["color"] = hex_color' in main, "цвет применяется к Mico сразу")
    check("onboarding.OnboardingDialog(cfg, on_color=recolor)" in main, "начальная настройка получает предпросмотр")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
