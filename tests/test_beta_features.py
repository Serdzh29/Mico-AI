"""Бета-функции: рабочее место, история копирования, итог дня — через тот же путь, что и фразы в чате.
Окна Windows и запуск программ подменены, хранилище настоящее (во временной папке)."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types, tempfile, time
sys.path.insert(0, ROOT)
_TMP = tempfile.mkdtemp()
_os.environ["APPDATA"] = _TMP
for m in ["mss", "psutil", "win32gui", "win32process", "win32con", "requests", "PIL", "PIL.Image", "pyautogui"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
class _RE(Exception):
    pass
sys.modules["requests"].RequestException = _RE

import version, features, workspace, clipbuf, commands
import winctl as W
import storage
import brain as B

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

# --- всё тестируем в бета-сборке на бета-канале ---
version.BUILD_CHANNEL = "beta"
BETA = {"update_channel": "beta"}

class _Store(storage.Store):
    pass

def make_brain(cfg):
    b = B.Brain.__new__(B.Brain)
    b.cfg = cfg
    b.store = storage.Store()
    b.save_cfg = lambda: None
    return b

# ================= 1. Рабочее место =================
check(workspace.command("запомни рабочее место") == "save")
check(workspace.command("сохрани мое рабочее место") == "save")
check(workspace.command("восстанови рабочее место") == "restore")
check(workspace.command("открой моё рабочее место") == "restore")
check(workspace.command("какая погода") is None)
check(workspace.command("подготовь рабочее место") is None, "подготовь рабочее место — это планировщик, не эта функция")

real_files = []
for name in ("notepad.exe", "calc.exe", "explorer.exe", "python.exe", "chrome.exe"):
    p = _os.path.join(_TMP, name)
    open(p, "w").close()
    real_files.append(p)
wins = [{"proc": "notepad.exe", "exe": real_files[0], "title": "a"},
        {"proc": "notepad.exe", "exe": real_files[0], "title": "b"},          # дубль окна
        {"proc": "explorer.exe", "exe": real_files[2], "title": "c"},         # системное
        {"proc": "python.exe", "exe": real_files[3], "title": "d"},           # сам Mico
        {"proc": "calc.exe", "exe": real_files[1], "title": "e"},
        {"proc": "ghost.exe", "exe": _os.path.join(_TMP, "nope.exe"), "title": "f"}]  # файла нет
picked = workspace.pick(wins)
check([a["proc"] for a in picked] == ["notepad.exe", "calc.exe"], picked)

cfg = dict(BETA)
saved = workspace.save(cfg, wins, now=1000)
check(len(saved) == 2 and cfg["workspace"]["apps"] == saved, "сохранилось в настройках")
check(len(workspace.pick([{"proc": f"app{i}.exe", "exe": real_files[0], "title": "t"}
                          for i in range(20)])) == workspace.MAX_APPS, "не больше MAX_APPS программ")

todo = workspace.plan_restore(cfg, running={"notepad.exe"})
check([a["proc"] for a in todo] == ["calc.exe"], "уже открытое не открываем повторно")
check(workspace.plan_restore({}, set()) == [], "без сохранённого рабочего места — пусто")

# через бот: запомнить, потом восстановить с подтверждением
brain = make_brain(cfg)
W.visible_apps = lambda: wins
W.running_names = lambda: {"notepad.exe"}
launched = []
W.launch = lambda exe: (launched.append(exe), True)[1]

r = brain._beta_command("запомни рабочее место", "запомни рабочее место")
check(r and "notepad" in r.text and "calc" in r.text, r and r.text)
commands._PENDING.update(fn=None, until=0)
r = brain._beta_command("восстанови рабочее место", "восстанови рабочее место")
check(r and "calc" in r.text and "да" in r.text, r and r.text)
check(launched == [], "до подтверждения ничего не открываем")
r = commands._pending("да")
check(launched == [real_files[1]], launched)
check(r and "1 из 1" in r.text, r and r.text)

# ================= 2. История копирования =================
c = clipbuf.command("найди что я копировал про договор")
check(c == ("search", "договор"), c)
check(clipbuf.command("что я копировал про договор") == ("search", "договор"))
check(clipbuf.command("забудь историю копирования") == ("forget", None))
check(clipbuf.command("очисти историю буфера обмена") is None, "это Windows-очистка буфера, не наша")

check(clipbuf.looks_secret("мой пароль: 123"), "слово «пароль»")
check(clipbuf.looks_secret("Qx9!vLm2"), "одиночное слово из букв, цифр и знаков")
check(clipbuf.looks_secret("4276 1234 5678 9012"), "номер карты")
check(not clipbuf.looks_secret("Договор №15 от 3 октября"), "обычный текст")
check(not clipbuf.looks_secret("https://example.com/page2"), "ссылка — не пароль")
check(not clipbuf.should_keep("текст", "keepass.exe"), "менеджер паролей не сохраняем")
check(not clipbuf.should_keep("x" * 3000, "chrome.exe"), "слишком длинное не сохраняем")
check(clipbuf.should_keep("Договор с ООО Ромашка", "winword.exe"))

store = storage.Store()
store.forget_clips()
rec = clipbuf.Recorder(store)
check(rec.offer("Договор с ООО Ромашка №15", "winword.exe", now=100))
check(not rec.offer("Договор с ООО Ромашка №15", "winword.exe", now=101), "повтор не пишем дважды")
check(rec.offer("Счёт за март на 12 000 рублей", "chrome.exe", now=102))
check(not rec.offer("мой пароль 111", "keepass.exe", now=103), "из менеджера паролей не пишем")
check(not rec.offer("Qx9!vLm2", "chrome.exe", now=104), "пароль не пишем")
rows = store.list_clips()
check([t for _, t in rows] == ["Счёт за март на 12 000 рублей", "Договор с ООО Ромашка №15"], rows)

brain = make_brain(dict(BETA))
r = brain._beta_command("найди что я копировал про договор", "найди что я копировал про договор")
check(r and "Ромашка" in r.text and "Счёт" not in r.text, r and r.text)
r = brain._beta_command("найди что я копировал про юриста", "найди что я копировал про юриста")
check(r and "Ничего не нашёл" in r.text, r and r.text)
r = brain._beta_command("забудь историю копирования", "забудь историю копирования")
check(r and store.list_clips() == [], "история очищается")

# ================= 3. Итог дня удалён =================
check("day_summary" not in features.FEATURES, "итога дня нет в функциях")

# ================= 4. Гейтинг: в стабильной сборке этих команд нет =================
version.BUILD_CHANNEL = "stable"
check(features.enabled("workspace", BETA), "рабочее место доступно всем")
check(features.enabled("clipboard_search", BETA), "история копирования доступна всем")
brain = make_brain(dict(BETA))
check(brain._beta_command("запомни рабочее место", "запомни рабочее место") is not None, "рабочее место доступно и в стабильной")
check(brain._beta_command("итог дня", "итог дня") is None, "итога дня больше нет")
version.BUILD_CHANNEL = "beta"

print("ALL OK")
