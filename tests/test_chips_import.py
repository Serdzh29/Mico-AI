"""Регрессия: кнопки под чатом строятся для всех переключателей (раньше падало IndexError при импорте chips)."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types
sys.path.insert(0, ROOT)
for m in ["mss", "psutil", "PIL", "PIL.Image", "win32gui", "win32process", "win32con", "requests",
          "cryptography", "cryptography.fernet"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
sys.modules["cryptography.fernet"].Fernet = object
class _RE(Exception):
    pass
sys.modules["requests"].RequestException = _RE

import components
import chips

toggles = [t for t in components.TOGGLES if t.keys]
assert len(chips.TOGGLE_EMOJI) < len(components.TOGGLES), "тест теряет смысл, если эмодзи хватает на все переключатели"
built = [c for c in chips.CATALOG if c.id.startswith("t:")]
assert len(built) == len(toggles), (len(built), len(toggles))
assert all(c.label for c in built)
print("ALL OK", len(built), "toggle chips")
