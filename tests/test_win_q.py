import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types, re
sys.path.insert(0, ROOT)
for m in ["mss", "psutil", "PIL", "PIL.Image", "win32gui", "win32process", "win32con", "requests", "cryptography", "cryptography.fernet"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
sys.modules["cryptography.fernet"].Fernet = object
class RE(Exception): pass
sys.modules["requests"].RequestException = RE
import brain as B, windows_info as W
opened = []
W.open_setting = lambda uri: opened.append(uri) or True
W.current_build = lambda: (26200, 6899)
class FB:
    _windows_question = B.Brain._windows_question
    cfg = {"update_channel": "stable"}
fb = FB()
for q in ["где найти настройку bluetooth", "как изменить тему", "какая у меня версия windows", "что нового в сборке", "как приготовить борщ"]:
    ql = q.lower()
    r = fb._windows_question(q, ql)
    print(f"{q!r:36} ->", (r.text.splitlines()[0] if r else None))
print("opened:", opened)
assert opened == ["ms-settings:bluetooth", "ms-settings:colors"], opened
print("ALL OK")
