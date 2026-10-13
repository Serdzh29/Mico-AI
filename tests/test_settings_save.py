"""Сохранение настроек: запись не портит файл, ошибка автозапуска не мешает сохранить остальное,
уведомления будят Mico. Qt подменён заглушкой; проверяется логика."""
import os as _os, sys, types, tempfile, json
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_TMP = tempfile.mkdtemp()
_os.environ["APPDATA"] = _TMP

class _Any:
    def __init__(self, *a, **k): pass
    def __call__(self, *a, **k): return _Any()
    def __getattr__(self, n): return _Any()
    def __iter__(self): return iter(())
    def __bool__(self): return False
class _Mod(types.ModuleType):
    def __getattr__(self, n):
        if n.startswith("__"): raise AttributeError(n)
        return _Any
for m in ["PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets", "mss", "psutil", "win32gui", "win32process",
          "win32con", "requests", "PIL", "PIL.Image", "pyautogui", "win32crypt"]:
    sys.modules[m] = _Mod(m)
sys.modules["PIL"].Image = _Any()
import main as M
import autostart

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

# 1. запись атомарная: при ошибке сериализации старый файл остаётся целым
M.CFG_PATH = _os.path.join(_TMP, "config.json")
M.save_cfg({"a": 1})
check(json.load(open(M.CFG_PATH, encoding="utf-8")) == {"a": 1})
try:
    M.save_cfg({"a": 2, "bad": object()})          # object() не сериализуется
except TypeError:
    pass
check(json.load(open(M.CFG_PATH, encoding="utf-8")) == {"a": 1}, "старый конфиг не должен пострадать")
M.save_cfg({"a": 3})
check(json.load(open(M.CFG_PATH, encoding="utf-8")) == {"a": 3}, "нормальная запись работает")

# 1б. запись работает, даже если переименование файла запрещено (как при блокировке антивирусом)
import os as _o
_real_replace = _o.replace
def _no_replace(*a, **k):
    raise PermissionError("файл занят")
_o.replace = _no_replace
try:
    M.save_cfg({"b": 7})
    check(json.load(open(M.CFG_PATH, encoding="utf-8")) == {"b": 7}, "сохраняем без переименования")
finally:
    _o.replace = _real_replace
check("os.replace" not in open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read().split("def save_cfg")[1].split("def ")[0],
      "save_cfg не должен переименовывать файл")

# 2. accept: настройки сохраняются, даже если автозапуск падает с исключением
class Ctl:
    def __init__(self, v=False): self.v = v
    def isChecked(self): return self.v
    def currentData(self): return "x"
    def currentText(self): return "Яндекс"
    def value(self): return 1
    def text(self): return "abc"
    def setChecked(self, v): self.v = v
class Fake: pass
def make_dialog():
    f = Fake()
    f.cfg = {"update_channel": "stable", "search_url": "", "greet_on_start": True}
    f.orig = dict(f.cfg)
    for name in ["beta_pick","quiet","updchk","sleep_min","pbr","pbr_min","greet","keep","se","outline","linked",
                 "city","mem","ini","ini_min","locc","auto","hk_chat","hk_tr","tm","vm","size_pick","mmax",
                 "cmode","ccount"]:
        setattr(f, name, Ctl(False))
    f.se = Ctl(False); f.se.currentText = lambda: "Яндекс"
    f.auto = Ctl(True)
    f._phrases = []
    f._save_chips = lambda: None
    f._menu_ids = lambda: []
    f._greet_ids = lambda: []
    f.cfg["settings_size"] = None
    return f

saved, warned = [], []
M.save_cfg = lambda cfg: saved.append(dict(cfg))
M.QMessageBox = types.SimpleNamespace(warning=lambda *a, **k: warned.append(a))

def run_accept(f):
    try:
        M.SettingsDialog.accept(f)
    except TypeError as e:
        if "super" not in str(e):                  # только ошибка заглушки на super() допустима
            raise

autostart.install = lambda *a, **k: (_ for _ in ()).throw(OSError("schtasks недоступен"))
autostart.remove = lambda *a, **k: (True, "")
f = make_dialog()
run_accept(f)
check(saved, "настройки сохранены, даже если автозапуск упал")
check(saved[-1].get("search_url", "").startswith("https://yandex"), saved[-1].get("search_url"))
check(warned, "ошибка автозапуска показана пользователю после сохранения")

saved.clear(); warned.clear()
autostart.install = lambda *a, **k: (False, "нет прав")
f = make_dialog()
run_accept(f)
check(saved and warned, "при отказе автозапуска настройки всё равно сохраняются")
check(saved[-1].get("autostart") is None or saved[-1].get("autostart") is False, "флажок не считаем включённым, если задача не создана")

# 3. неизвестный поисковик не роняет сохранение
saved.clear()
autostart.install = lambda *a, **k: (True, "")
f = make_dialog(); f.se.currentText = lambda: "НеизвестныйПоиск"
run_accept(f)
check(saved and saved[-1]["search_url"].startswith("https://www.google"), saved and saved[-1].get("search_url"))

# 4. уведомление помодоро будит спящего Mico, но не открывает чат
src = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
body = src.split("    def on_reminder(self, text):")[1].split("    def on_link")[0]
check("self.blob.wake(silent=True)" in body, "on_reminder будит Mico тихо")
check("woke" not in body and "open_chat" not in body, "чат при уведомлении не открывается")
print("ALL OK")
