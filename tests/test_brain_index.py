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
import brain as B, indexer as I
class FakeStore:
    def load_index(self):
        return [{"kind": "app", "name": "Telegram", "path": r"C:\x\Telegram.lnk", "mtime": 5, "size": 1},
                {"kind": "photo", "name": "кот на диване.jpg", "path": r"C:\Pictures\кот.jpg", "mtime": 3, "size": 1},
                {"kind": "game", "name": "Hades", "path": r"C:\Games\Hades", "mtime": 1, "size": 0}]
class FB:
    store = FakeStore(); _idx = None
    index_records = B.Brain.index_records
    _index_reply = B.Brain._index_reply
    _index_command = B.Brain._index_command
    start_index = lambda self: True
b = FB()
r = b._index_reply("найди телеграм")
print("text:", r.text.replace("\n", " | "))
print("html has link:", 'href="mico-open:C:\\x\\Telegram.lnk"' in r.html)
print("no hits ->", b._index_reply("найди космолёт"))
print("status:", indexer_status := I.status_text())
r2 = b._index_command("проиндексируй компьютер")
print("start:", r2.text[:40])
