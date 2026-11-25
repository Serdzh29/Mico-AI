"""Третий раунд: волны, остров сна, постоянное прослушивание «Мико» и качество диктовки. Без Qt."""
import os as _os, sys, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def _src(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()





def test_waves_are_less_transparent_and_smoother():
    ui = _src("assist/ui.py")
    check("def _draw_edges" in ui and "QLinearGradient" in ui, "полоски по краям — мягкие градиенты")
    check("fade(" in ui and "setColorAt(0.55" in ui, "градиент гаснет к центру без резкой линии")
    check("wave_opacity" not in ui, "прозрачности нет: полоски всегда видны")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
