"""Компоненты со скриншотов «Параметров»: распознавание фраз, вызовы UI Automation и ссылки по теме.
Работает без Windows: системные вызовы подменены записью."""
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

from urllib.parse import unquote
import winctl as W
import components as K
import commands as C

calls = []
W.run_elevated = lambda cmd, timeout=180: (calls.append(("admin", cmd)), (True, ""))[1]
W.reg_set = lambda path, name, value, kind="dword", hive="HKCU": calls.append(("reg", hive, path, name, value, kind))
W.broadcast_setting = lambda *a, **k: None
W.shell_refresh = lambda: None
W.ui_setting = lambda page, label, on=True, mode="toggle", timeout=14: (
    calls.append(("ui", page, label, on, mode)), (True, ""))[1]
W.press = lambda *a, **k: calls.append(("press", a))
W.run_quiet = lambda *a, **k: True
opened, webopen = [], []
import os
os.startfile = lambda p: opened.append(p)
C.webbrowser = types.SimpleNamespace(open=lambda u: webopen.append(u))
C.SEARCH_URL = "https://www.google.com/search?q="
C.warmup = lambda: None
K.subprocess = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=0),
                                     CalledProcessError=Exception)
C.subprocess = K.subprocess


def run(q):
    calls.clear(); opened.clear(); webopen.clear()
    r = C.handle(q)
    return r, list(calls), list(opened), list(webopen)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# --- фразы со скриншотов: распознаются и вызывают нужный способ ---
r, c, _, _ = run("включи режим разработчика")
check(any(x[0] == "admin" and "AppModelUnlock" in x[1] and "AllowDevelopmentWithoutDevLicense" in x[1] for x in c)
      or any(x[0] == "admin" and "AllowDevelopmentWithoutDevLicense" in x[1] for x in c), (r, c))
check("Режим разработчика" in r.text, r.text)

r, c, _, _ = run("выключи портал устройств")
check(("ui", "ms-settings:developers", "Портал устройств", False, "toggle") in c, c)

r, c, _, _ = run("включи обнаружение устройств")
check(("ui", "ms-settings:developers", "Обнаружение устройств", True, "toggle") in c, c)

r, c, _, _ = run("выключи журнал буфера обмена на ваших устройствах")
check(any(x[0] == "reg" and x[3] == "CloudClipboardAutomaticUpload" and x[4] == 0 for x in c), c)

r, c, _, _ = run("включи длинные пути")
check(any(x[0] == "admin" and "LongPathsEnabled" in x[1] and "/d 1" in x[1] for x in c), c)

r, c, _, _ = run("выключи sudo")
check(any(x[0] == "admin" and "sudo config --enable disable" in x[1] for x in c), c)

r, c, _, _ = run("выключи завершение задачи на панели задач")
check(any(x[0] == "reg" and x[3] == "TaskbarEndTask" and x[4] == 0 for x in c), c)

r, c, _, _ = run("включи монозвук")
check(any(x[0] == "reg" and x[3] == "AccessibilityMonoMixState" and x[4] == 1 for x in c), c)

r, c, _, _ = run("выключи встряхивание заголовка окна")
check(any(x[0] == "reg" and x[3] == "DisallowShaking" and x[4] == 1 for x in c), c)

r, c, _, _ = run("включи обмен с устройствами поблизости")
check(("ui", "ms-settings:crossdevice", "Только мои устройства", True, "select") in c, c)

r, c, _, _ = run("выключи обмен с устройствами поблизости")
check(("ui", "ms-settings:crossdevice", "Отключено", True, "select") in c, c)

r, c, _, _ = run("выключи прикрепление окон")
check(any(x[0] == "reg" and x[3] == "WindowArrangementActive" and x[4] == "0" for x in c), c)

r, c, _, _ = run("выключи отключение экрана по таймеру")
check(r is not None, "no reply for screen timeout")

# --- действия: буфер просит подтверждение, сброс не выполняется сам ---
r, c, _, _ = run("очисти буфер обмена")
check("Очистить историю буфера обмена" in r.text and not any(x[0] == "ui" for x in c), (r.text, c))
r, c, _, _ = run("да")
check(("ui", "ms-settings:clipboard", "Очистить", True, "click") in c, c)

r, c, o, _ = run("сбрось пк")
check("ms-settings:recovery" in o, o)
check("не запускаю" in r.text, r.text)
check(not any(x[0] in ("admin", "ui") for x in c), c)

print("ALL OK")
