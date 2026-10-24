"""Кнопка «Копировать» под ответами Mico AI в чате."""
import os as _os

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def _src(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def test_copy_button_only_under_mico_replies():
    s = _src("aichat.py")
    check('if kind == "mico" and str(text or "").strip():' in s, "кнопка только у ответов Mico")
    check('"Копировать"' in s and 'setObjectName("ghost")' in s, "кнопка в тихом стиле")
    check("clipboard().setText(text)" in s, "копирует в буфер")
    check("Скопировано" in s, "показывает подтверждение")


if __name__ == "__main__":
    test_copy_button_only_under_mico_replies()
    print("OK test_copy_button_only_under_mico_replies")
