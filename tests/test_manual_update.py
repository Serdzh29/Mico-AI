"""Ручная проверка версии: «есть ли новая версия Mico?» работает без суточного ограничения."""
import os as _os, sys, types, tempfile, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_os.environ["APPDATA"] = tempfile.mkdtemp()
for m in ["mss", "psutil", "win32gui", "win32process", "win32con", "requests", "PIL", "PIL.Image", "pyautogui"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
class _RE(Exception):
    pass
sys.modules["requests"].RequestException = _RE
import version, updatecheck as U, commands
import brain as B

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def make_brain(cfg):
    b = B.Brain.__new__(B.Brain)
    b.cfg, b.save_cfg = cfg, (lambda: None)
    return b

opened = []
import webbrowser
webbrowser.open = lambda url: opened.append(url)
_ORIG_VERSION = version.APP_VERSION            # восстановим в конце, чтобы другие тесты видели настоящую версию
version.APP_VERSION = "2026.10.1304"            # установлена старая версия

# фразы
for q in ["есть ли новая версия mico", "проверь версию мико", "проверь обновления mico"]:
    check(B.Brain.MANUAL_UPDATE.fullmatch(q), q)
check(not B.Brain.MANUAL_UPDATE.fullmatch("проверь обновления"), "обновления Windows — это другая команда")

# новая версия есть: спрашиваем, потом открываем страницу
U.fetch_latest = lambda api_url=None, timeout=6: {"tag": "v2026.10.1304a", "url": "https://github.com/x/releases/latest", "notes": ""}
cfg = {"update_checked_at": time.time()}          # проверяли минуту назад — ручная всё равно проверяет
b = make_brain(cfg)
r = b._manual_update("есть ли новая версия mico")
check(r and "1304(a)" in r.text and "Скажи «да»" in r.text, r and r.text)
check(not opened, "до «да» ничего не открываем")
r = commands._pending("да")
check(opened == ["https://github.com/x/releases/latest"] and r and "Открыл" in r.text, opened)

# уже последняя версия
version.APP_VERSION = "2026.10.1304(a)"
r = make_brain({})._manual_update("проверь версию мико")
check(r and "последняя" in r.text, r and r.text)

# нет связи
U.fetch_latest = lambda api_url=None, timeout=6: None
r = make_brain({})._manual_update("есть ли новая версия mico")
check(r and "Не смог проверить" in r.text, r and r.text)

# обычные фразы не трогаем
check(make_brain({})._manual_update("какая погода") is None)
print("ALL OK")
version.APP_VERSION = _ORIG_VERSION
