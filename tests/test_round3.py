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
    ui = _src("intel_ui.py")
    check("a_bot" in ui and "round(255 * k)" in ui and "wave_opacity" in ui, "прозрачность волн — из настроек")
    check("quadTo(" in ui and "layer(1.7" in ui and "layer(0.0" in ui, "две волны, плавные кривые")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
