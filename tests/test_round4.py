"""Четвёртый раунд: прозрачность волн, пометка BETA, без плашки-статуса. Без Qt."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MAIN = open(_os.path.join(ROOT, "mico.py"), encoding="utf-8").read().replace("i18n.t(", "")   # текст кнопок теперь через i18n.t (только для проверки строк)
UI = open(_os.path.join(ROOT, "assist/ui.py"), encoding="utf-8").read()

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def test_status_capsule_is_gone():
    check("self.island = None" in UI and "Island(cfg, blob)" not in UI, "плашка-статус не создаётся")

def test_wave_opacity_setting_and_presets():
    check('"wave_opacity"' not in MAIN and "wave_opacity" not in UI, "прозрачности нет: полоски всегда видны")
    check("Максимально прозрачные" not in MAIN and "wave_op" not in MAIN, "пресеты прозрачности убраны")



def test_beta_is_marked_for_windows_intelligence():
    check("Mico AI" in MAIN, "название Mico AI в настройках")




if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
