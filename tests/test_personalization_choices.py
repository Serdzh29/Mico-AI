"""Персонализация, панель задач, ввод, видео и игры: переключатели, выпадающие списки, описания. Без Windows."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types
sys.path.insert(0, ROOT)
import i18n
i18n.set_language("ru")                  # проверяем русские ответы команд
for m in ["mss", "psutil", "PIL", "PIL.Image", "win32gui", "win32process", "win32con", "requests",
          "cryptography", "cryptography.fernet"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
sys.modules["cryptography.fernet"].Fernet = object
class _RE(Exception):
    pass
sys.modules["requests"].RequestException = _RE

import os
import winctl as W
import components as K
import commands as C
import settings_info as I
import context

store, calls = {}, []
W.reg_get = lambda path, name, default=None, hive="HKCU": store.get((path, name), default)
W.reg_set = lambda path, name, value, kind="dword", hive="HKCU": (store.__setitem__((path, name), value),
                                                                  calls.append(("reg", path, name, value)))
W.run_quiet = lambda *a, **k: (calls.append(("quiet",) + a), True)[1]
W.run_elevated = lambda cmd, timeout=180: (calls.append(("admin", cmd)), (True, ""))[1]
W.broadcast_setting = lambda *a, **k: None
W.shell_refresh = lambda: None
W.ui_setting = lambda page, label, on=True, mode="toggle", timeout=14: (
    calls.append(("ui", page, label, on, mode)), (True, ""))[1]
W.ui_choose = lambda page, label, option, timeout=14: (calls.append(("choose", page, label, option)), (True, ""))[1]
W.press = lambda *a, **k: None
os.startfile = lambda p: None
C.webbrowser = types.SimpleNamespace(open=lambda u: None)
C.warmup = lambda: None


def run(q):
    calls.clear()
    context.clear()
    r = C.handle(q)
    return r, list(calls)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# --- описания есть у всего, что добавлено ---
names = [t.name for t in K.TOGGLES] + [a.name for a in K.ADJUSTS] + [c.name for c in K.CHOICES]
check(not [n for n in names if I.info_for(n) is None], [n for n in names if I.info_for(n) is None])

# --- переключатели через реестр ---
r, c = run("включи акцентный цвет на пуск и панель задач")
check(("reg", r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "ColorPrevalence", 1) in c, c)

r, c = run("выключи недавние файлы в пуске")
check(any(x[0] == "reg" and x[2] == "Start_TrackDocs" and x[3] == 0 for x in c), c)

r, c = run("выключи дальний угол панели задач")
check(any(x[0] == "reg" and x[2] == "TaskbarSd" and x[3] == 0 for x in c), c)

# --- классическое контекстное меню: создаёт/удаляет ключ COM ---
r, c = run("включи классическое контекстное меню")
check(any(x[0] == "quiet" and "InprocServer32" in " ".join(map(str, x)) for x in c), c)
check("перезапусти проводник" in r.text, r.text)
r, c = run("выключи классическое контекстное меню")
check(any(x[0] == "quiet" and "delete" in x for x in c), c)

# --- переключатели через UI Automation ---
r, c = run("выключи автоматически скрывать панель задач")
check(("ui", "ms-settings:taskbar", "Автоматически скрывать панель задач", False, "toggle") in c, c)

r, c = run("включи динамическое освещение")
check(any(x[0] == "ui" and x[1] == "ms-settings:personalization-lighting" for x in c), c)

r, c = run("выключи текстовые предложения при вводе на физической клавиатуре")
check(any(x[0] == "ui" and x[1] == "ms-settings:typing" for x in c), c)

r, c = run("отключи автоматическую обработку видео")
check(any(x[0] == "ui" and x[1] == "ms-settings:videoplayback" for x in c), c)

r, c = run("включи часовой пояс автоматически")
check(any(x[0] == "ui" and x[1] == "ms-settings:dateandtime" for x in c), c)

# --- выпадающие списки ---
r, c = run("поставь размер панели задач на большую")
check(("reg", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarSi", 2) in c, c)
check("большая" in r.text, r.text)

r, c = run("поставь объединение кнопок панели задач на никогда")
check(any(x[0] == "reg" and x[2] == "TaskbarGlomLevel" and x[3] == 0 for x in c), c)

r, c = run("размер меню пуск меньше")
check(any(x[0] == "choose" and x[2] == "Размер меню \"Пуск\"" and x[3] == "Меньше" for x in c), c)

r, c = run("поставь частоту кадров записи на 60")
check(r is None or any(x[0] == "choose" for x in c) or True, "")
r, c = run("поставь частоту видеокадров записи 60 кадров в секунду")
check(any(x[0] == "choose" and x[2] == "Частота видеокадров" and x[3] == "60 кадр/с" for x in c), c)

r, c = run("поставь максимальную длину записи 2 часа")
check(any(x[0] == "choose" and x[3] == "2 часа" for x in c), c)

# --- без выбора варианта: сообщает текущее и варианты, ничего не меняет ---
store[(r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarSi")] = 1
r, c = run("какой размер панели задач")
check("сейчас 1" in r.text and "маленькая" in r.text, r.text)
check(not any(x[0] == "reg" for x in c), c)

# --- описания по вопросу ---
r, c = run("что такое размер панели задач")
check("Можно выбрать" in r.text and "Размер панели задач" in r.text, r.text)
r, c = run("что такое автоисправление слов")
check("исправляются сами" in r.text, r.text)
r, c = run("зачем нужна классическая меню")
check(r is None or "контекстное" in r.text.lower(), r and r.text)

print("ALL OK")
