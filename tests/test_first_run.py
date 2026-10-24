"""Первый запуск: чат и приветствие не открываются поверх начальной настройки. Проверки без Qt."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_no_chat_or_greeting_over_onboarding():
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    check("first_run = not cfg.get(\"tour_done\")" in src, "признак первого запуска")
    check("and not first_run:\n        QTimer.singleShot(700, greet)" in src, "приветствие не открывается при первом запуске")
    check("if not relaunch and not first_run:\n        QTimer.singleShot(900, open_chat_on_start)" in src,
          "чат не открывается при первом запуске")
    check('cfg["tour_done"] = True' in src and "dlg.exec()" in src, "начальная настройка по-прежнему показывается")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
