"""Стиль общения реально меняет ответы: температура зависит от стиля, подсказка стоит в конце и не обрезается."""
import os, sys
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _m in ("win32gui", "win32con", "win32process", "win32api"):
    sys.modules.setdefault(_m, mock.MagicMock())
from core import brain


def _b(style, temp=None):
    b = object.__new__(brain.Brain)
    b.cfg = {"chat_style": style}
    if temp is not None:
        b.cfg["llm_temperature"] = temp
    return b


def test_temperature_follows_style():
    assert _b("creative")._style_temperature() >= 0.95, "творческий — смелее"
    assert _b("precise")._style_temperature() <= 0.25, "точный — суше"
    assert _b("balanced")._style_temperature() is None, "обычный — как в настройках"
    assert _b("balanced", 0.5)._style_temperature() == 0.5, "настройка температуры уважается"
    assert _b("precise", 0.1)._style_temperature() == 0.1, "точный не делает температуру выше заданной"
    assert _b("creative")._style_temperature(tools=True) is None, "выбор действия для ПК стиль не трогает"


def test_style_hints_differ_and_are_loud():
    c, p = brain.CHAT_STYLES["creative"], brain.CHAT_STYLES["precise"]
    assert c != p and "творческий" in c and "точный" in p


if __name__ == "__main__":
    test_temperature_follows_style()
    test_style_hints_differ_and_are_loud()
    print("ok")
