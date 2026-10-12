import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types
sys.path.insert(0, ROOT)
for m in ["mss", "psutil", "PIL", "PIL.Image", "win32gui", "win32process", "win32con", "requests", "cryptography", "cryptography.fernet"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
sys.modules["cryptography.fernet"].Fernet = object
class RE(Exception): pass
sys.modules["requests"].RequestException = RE
sys.modules["requests"].post = lambda *a, **k: None
import brain as B, commands as C, planner as P
from actions import Reply

ran = []
def fake_handle(q, notify=None, last_hwnd=None):
    ran.append(q)
    return Reply(f"ok: {q}", "happy")
C.handle = fake_handle

class FakeBrain:
    cfg = {"text_model": "m"}
    notify = staticmethod(lambda t: None)
    last_hwnd = staticmethod(lambda: None)
    _handled = False
    def _chat(self, user, model, **k):
        return '{"steps": ["открой телеграм", "выключи пк", "громкость 30", "не беспокоить"]}'
    _plan = B.Brain._plan
    _run_plan = B.Brain._run_plan

fb = FakeBrain()
r = fb._plan("подготовь к работе")
print("question:\n" + r.text)
print("pending set:", C._PENDING["fn"] is not None)
ans = C._pending("да")
print("after 'да':", ans.text if ans else None)
print("executed:", ran)
assert ran == ["открой телеграм", "громкость 30", "не беспокоить"], ran
ran.clear()
fb._plan("подготовь к работе")
print("after 'нет':", C._pending("нет").text)
assert ran == []
# остановка на сбое шага
C.handle = lambda q, *a, **k: None if "громкость" in q else Reply("ok", "happy")
rr = fb._run_plan(["открой телеграм", "громкость 30", "не беспокоить"])
print("stop on failure:", rr.text)
print("ALL PLAN TESTS OK")
