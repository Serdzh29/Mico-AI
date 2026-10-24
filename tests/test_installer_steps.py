"""Мастер установки и удаления: точки шагов вместо текста, один стиль для обоих мастеров."""
import os as _os

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def _src():
    return open(_os.path.join(ROOT, "installer.py"), encoding="utf-8").read()


def test_wizard_uses_step_dots():
    s = _src()
    check("class StepDots(QWidget)" in s, "есть виджет точек шагов")
    check("self.step_lbl = StepDots(4)" in s, "мастер установки: 4 экрана")
    check("self.step_lbl = StepDots(3)" in s, "мастер удаления: 3 экрана")
    check("self.step_lbl.set_current(i)" in s, "точки переключаются на каждом экране")


def test_dots_follow_wizard_palette():
    s = _src()
    check('c["accent"]' in s and 'c["box_edge"]' in s, "точки берут цвета из палитры мастера")
    check("QRectF(x, 2, 20, 6)" in s, "текущий шаг — вытянутая таблетка")


if __name__ == "__main__":
    test_wizard_uses_step_dots()
    print("OK test_wizard_uses_step_dots")
    test_dots_follow_wizard_palette()
    print("OK test_dots_follow_wizard_palette")
