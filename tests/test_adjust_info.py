"""Регулировка значений (ползунки, «больше/меньше», «назад»), описания настроек и новые переключатели
со скриншотов VPN / Wi-Fi / Ethernet / мыши / клавиатуры / принтеров / прокси. Без Windows."""
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

import winctl as W
import components as K
import commands as C
import settings_info as I
import context
from urllib.parse import unquote

store = {}            # имитация реестра
calls = []
W.reg_get = lambda path, name, default=None, hive="HKCU": store.get((path, name), default)
W.reg_set = lambda path, name, value, kind="dword", hive="HKCU": (store.__setitem__((path, name), value),
                                                                  calls.append(("reg", path, name, value)))
W._spi = lambda action, value, update=3: (calls.append(("spi", action, value)), True)[1]
W.run_quiet = lambda *a, **k: (calls.append(("quiet",) + a), True)[1]
W.run_elevated = lambda cmd, timeout=180: (calls.append(("admin", cmd)), (True, ""))[1]
W.broadcast_setting = lambda *a, **k: None
W.shell_refresh = lambda: None
W.ui_setting = lambda page, label, on=True, mode="toggle", timeout=14: (
    calls.append(("ui", page, label, on, mode)), (True, ""))[1]
W.press = lambda *a, **k: None
import os
opened, webopen = [], []
os.startfile = lambda p: opened.append(p)
C.webbrowser = types.SimpleNamespace(open=lambda u: webopen.append(u))
C.warmup = lambda: None


def run(q):
    calls.clear()
    context.clear()
    r = C.handle(q)
    return r, list(calls)


def run_keep(q):
    """Как run, но без очистки памяти диалога (для «назад»/«ещё»)."""
    calls.clear()
    r = C.handle(q)
    return r, list(calls)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# --- каждая настройка имеет описание ---
names = [t.name for t in K.TOGGLES] + [a.name for a in K.ADJUSTS]
missing = [n for n in names if I.info_for(n) is None]
check(not missing, f"нет описания у: {missing}")

# --- регулировка: прямое значение ---
r, c = run("поставь скорость указателя мыши на 15")
check(("reg", r"Control Panel\Mouse", "MouseSensitivity", "15") in c, c)
check(("spi", 0x0071, 15) in c, c)
check("15 из 20" in r.text, r.text)

r, c = run("установи строки прокрутки на 5")
check(("spi", 0x0069, 5) in c, c)

r, c = run("задержка повтора символов на 2")
check(("spi", 0x0017, 2) in c, c)

r, c = run("частота повтора символов на 31")
check(("spi", 0x000B, 31) in c, c)

# --- границы ---
r, c = run("поставь скорость указателя на 99")
check("от 1 до 20" in r.text, r.text)
check(not any(x[0] == "spi" for x in c), c)

# --- таймеры питания: минуты и часы ---
r, c = run("поставь гибернацию через 2 часа")
check(("quiet", "powercfg", "/change", "hibernate-timeout-ac", "120") in c, c)

r, c = run("отключение экрана через 10 минут")
check(("quiet", "powercfg", "/change", "monitor-timeout-ac", "10") in c, c)

# --- относительно: больше/меньше, ещё, назад ---
store[(r"Control Panel\Mouse", "MouseSensitivity")] = "10"
r, c = run("скорость указателя больше")
check(("spi", 0x0071, 12) in c, c)            # шаг 2
r, c = run_keep("ещё")
check(("spi", 0x0071, 14) in c, c)
r, c = run_keep("назад")
check(("spi", 0x0071, 12) in c, c)

# --- описание и текущее значение ---
store[(r"Control Panel\Desktop", "WheelScrollLines")] = "4"
r, c = run("что такое строки прокрутки")
check("Строки прокрутки" in r.text and "Сейчас: 4" in r.text, r.text)
r, c = run("расскажи про скорость указателя мыши")
check("Скорость указателя мыши" in r.text and "Скажи" in r.text, r.text)

# --- описание переключателя с текущим состоянием ---
store[(r"Software\Microsoft\Windows NT\CurrentVersion\Windows", "LegacyDefaultPrinterMode")] = 1
r, c = run("зачем нужна фокусировка")
check("Фокусировка" in r.text and "включи" in r.text.lower() or "открой" in r.text.lower(), r.text)
r, c = run("что такое управление принтером по умолчанию")
check("выключено" in r.text, r.text)

# --- что-то не из настроек: не отвечаем (уйдёт к модели) ---
r, c = run("что такое фотосинтез")
check(r is None, r and r.text)

# --- новые переключатели со скриншотов ---
r, c = run("выключи vpn в роуминге")
check(("ui", "ms-settings:network-vpn", "Разрешить VPN в роуминге", False, "toggle") in c, c)

r, c = run("включи случайные аппаратные адреса")
check(("ui", "ms-settings:network-wifi", "Случайные аппаратные адреса", True, "toggle") in c, c)

r, c = run("выключи лимитное подключение ethernet")
check(("ui", "ms-settings:network-ethernet", "Лимитное подключение", False, "toggle") in c, c)

r, c = run("выключи повышение точности указателя")
check(any(x[0] == "reg" and x[1] == r"Control Panel\Mouse" and x[2] == "MouseSpeed" and x[3] == "0" for x in c), c)

r, c = run("включи автоматическое определение прокси")
check(any(x[0] == "reg" and x[1].endswith("Internet Settings") and x[2] == "AutoDetect" and x[3] == 1 for x in c), c)

r, c = run("выключи windows управляет принтером по умолчанию")
check(any(x[0] == "reg" and x[2] == "LegacyDefaultPrinterMode" and x[3] == 1 for x in c), c)

r, c = run("отключи адаптер wi-fi")
check(r is not None and "подтверд" not in r.text.lower() and "Скажи" in r.text, r and r.text)
r, c = run("да")
check(any(x[0] == "admin" and "Native 802.11" in x[1] and "Disable-NetAdapter" in x[1] for x in c), c)

r, c = run("включи адаптер ethernet")
check(any(x[0] == "admin" and "802.3" in x[1] and "Enable-NetAdapter" in x[1] for x in c), c)


print("ALL OK")
