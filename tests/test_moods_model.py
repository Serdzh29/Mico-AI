"""Эмоции: модель знает все метки, её ответы (экран, буфер, журнал, инициатива) несут настроение,
сердечко не появляется само по себе. Без Windows и без модели."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types, re
sys.path.insert(0, ROOT)
for m in ["mss", "psutil", "PIL", "PIL.Image", "win32gui", "win32process", "win32con", "requests",
          "cryptography", "cryptography.fernet", "pyautogui"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
sys.modules["cryptography.fernet"].Fernet = object
class _RE(Exception):
    pass
sys.modules["requests"].RequestException = _RE

from core import emotions as E
from core import brain as B

# 1. модель видит все эмоции, которые умеет показать Mico
missing = [m for m in sorted(E.VALID) if f"[{m}]" not in B.MOOD_RULE]
assert not missing, f"в подсказке модели нет: {missing}"

# 2. Mico умеет показать каждую эмоцию из списка: в blob.py есть отрисовка
blob_src = open(_os.path.join(ROOT, "ui/blob.py"), encoding="utf-8").read()
not_drawn = [m for m in sorted(E.VALID) if m not in ("idle",) and f'"{m}"' not in blob_src]
assert not not_drawn, f"нет отрисовки для: {not_drawn}"

# 3. сердечко не выбирается случайно в спокойном состоянии
idle_line = [l for l in blob_src.split("\n") if "random.choice([" in l and "start_anim" in l]
assert idle_line and '"heart"' not in idle_line[0], idle_line

# 4. метка разбирается, ключевые слова дают нужную эмоцию
assert E.split_mood("[playful] Ой, ну держись!") == ("playful", "Ой, ну держись!")
assert E.split_mood("[tired] Пора отдохнуть") == ("sleepy", "Пора отдохнуть")
assert E.detect_emotion("ну ты и хитрец 😉") == "playful"

# 5. экран: снимок в облако не уходит, Mico честно говорит об этом и остаётся в настроении «любопытный»
class _Tracker:
    last_blocked = False
class _Brain(B.Brain):
    def __init__(self):
        self.tracker = _Tracker()
        self.cfg = {"llm_backend": "mico", "text_model": "t"}

r = _Brain()._screen_question("что на экране?")
assert r.mood == "curious" and "не рассматриваю" in r.text, (r.mood, r.text)

print("ALL OK")
