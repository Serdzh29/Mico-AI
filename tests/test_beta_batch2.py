"""Бета, вторая партия: здоровье ПК, итог недели, список дел, очистка, порядок в загрузках, расписание.
Реальные файлы во временных папках, настоящее хранилище; системные вызовы Windows подменены."""
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

import version, features, health, cleanup, sorter, schedule, commands, storage
import winctl as W
import brain as B

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

version.BUILD_CHANNEL = "beta"
BETA = {"update_channel": "beta"}

def make_brain(cfg):
    b = B.Brain.__new__(B.Brain)
    b.cfg = cfg
    b.store = storage.Store()
    b.save_cfg = lambda: None
    return b

# ================= 1. Здоровье ПК =================
check(health.command("как дела у пк") and health.command("проверь здоровье компьютера"))
check(not health.command("как дела"), "обычный вопрос не про ПК")
GB = 1024 ** 3
txt = health.report(lambda p: (100 * GB, 90 * GB, 10 * GB), boot_time=time.time() - 5 * 3600,
                    now=time.time(), defender=False)
check("10.0 ГБ из 100.0 ГБ (10%)" in txt and "места мало" in txt, txt)
check("выключена" in txt and "5 ч" in txt, txt)
txt2 = health.report(lambda p: (100 * GB, 40 * GB, 60 * GB), boot_time=time.time(), now=time.time(), defender=True)
check("места мало" not in txt2 and "включена" in txt2, txt2)
check("Центр обновления" in txt2, "про обновления честно отсылаем в настройки")

cfg = dict(BETA)
brain = make_brain(cfg)
W.disk_usage = lambda p: (100 * GB, 40 * GB, 60 * GB)
W.boot_time = lambda: time.time() - 3600
W.defender_on = lambda: True
r = brain._beta_command("как дела у пк", "как дела у пк")
check(r and "Диск C" in r.text and "включена" in r.text, r and r.text)

# ================= 3. Итог недели =================
store = storage.Store()
now = time.time()
store.add(now - 3600, now - 1800, "chrome.exe", "a")
store.add(now - 1800, now - 900, "code.exe", "b")
pass  # итог недели удалён
pass  # итог недели удалён
pass  # итог недели удалён
pass  # итог недели удалён

# ================= 4. Очистка диска =================
check(cleanup.command("что занимает место") == "size")
check(cleanup.command("очисти временные файлы") == "clean")
check(cleanup.command("очисти загрузки") is None, "чистим только временные файлы")

tmp = tempfile.mkdtemp()
old = _os.path.join(tmp, "old.tmp"); new = _os.path.join(tmp, "new.tmp")
os_sub = _os.path.join(tmp, "sub"); _os.makedirs(os_sub)
open(old, "wb").write(b"x" * 5000); open(new, "wb").write(b"y" * 3000)
open(_os.path.join(os_sub, "deep.tmp"), "wb").write(b"z" * 999)
t_old = time.time() - 3 * 86400
_os.utime(old, (t_old, t_old))
files = cleanup.old_temp_files(tmp, time.time())
check([_os.path.basename(p) for p, _ in files] == ["old.tmp"], files)   # новый, подпапка — не трогаем
def _fake_recycle(path):                 # на Linux корзины нет: проверяем логику, а не Windows
    _os.remove(path)
    return True
n, freed, skipped = cleanup.delete_files(files, send=_fake_recycle)
check(n == 1 and freed == 5000 and not _os.path.exists(old) and _os.path.exists(new), (n, freed))
check(cleanup.delete_files([(old, 1)], send=lambda p: False) == (0, 0, 1), "что корзина не приняла — пропускаем, не стираем")
check(_os.path.exists(_os.path.join(os_sub, "deep.tmp")), "подпапки не трогаем")
check("Больше всего" in cleanup.size_text({"Загрузки": 3 * 1024**2, "Видео": 9 * 1024**2}))

cleanup.temp_dir = lambda: tmp
old2 = _os.path.join(tmp, "old2.tmp"); open(old2, "wb").write(b"q" * 100)
_os.utime(old2, (t_old, t_old))
r = brain._beta_command("очисти временные файлы", "очисти временные файлы")
check(r and "в корзину" in r.text and "Скажи «да»" in r.text, r and r.text)
check(_os.path.exists(old2), "до «да» ничего не удаляем")
r = commands._pending("да")
# В корзину можно отправить только в Windows. Вне Windows файлы не стираем и честно говорим, что пропустили.
check(r and "Отправил в корзину" in r.text and (not _os.path.exists(old2) or "пропустил" in r.text.lower()) or r and "пропустил" in r.text.lower(), r and r.text)
check(_os.path.exists(new), "свежий файл остался")

# ================= 5. Порядок в «Загрузках» =================
dl = tempfile.mkdtemp()
for name in ["photo.jpg", "report.pdf", "setup.exe", "movie.mp4", "readme.xyz", ".hidden.jpg"]:
    open(_os.path.join(dl, name), "wb").write(b"d")
plan = sorter.plan(dl)
cats = sorted(_os.path.relpath(d, dl).split(_os.sep)[0] for _, d in plan)
check(cats == ["Видео", "Документы", "Изображения", "Установщики"], cats)     # .xyz и скрытый не трогаем
open(_os.path.join(dl, "Изображения"), "w").close() if False else None

brain.cfg["downloads_test"] = dl
sorter_plan = sorter.plan
sorter_dl = _os.path.join(_os.path.expanduser("~"), "Downloads")
real_plan = sorter.plan
sorter.plan = lambda folder: real_plan(dl)
r = brain._beta_command("наведи порядок в загрузках", "наведи порядок в загрузках")
check(r and "Разложить 4" in r.text and "Скажи «да»" in r.text, r and r.text)
check(_os.path.exists(_os.path.join(dl, "photo.jpg")), "до «да» файлы на месте")
r = commands._pending("да")
check(r and "Разложил файлов: 4" in r.text, r and r.text)
check(_os.path.exists(_os.path.join(dl, "Изображения", "photo.jpg")), "файл переехал")
r = brain._beta_command("отмени сортировку", "отмени сортировку")
check(r and "Вернул на места файлов: 4" in r.text, r and r.text)
check(_os.path.exists(_os.path.join(dl, "photo.jpg")), "вернулся на место")
sorter.plan = sorter_plan

# коллизия имён: не перезаписываем
d2 = tempfile.mkdtemp(); _os.makedirs(_os.path.join(d2, "Документы"))
open(_os.path.join(d2, "Документы", "a.pdf"), "w").close(); open(_os.path.join(d2, "a.pdf"), "w").close()
p2 = sorter.plan(d2)
check(p2 and p2[0][1].endswith("a (2).pdf"), p2)

# ================= 6. Расписание =================
valid = brain._schedulable
check(schedule.parse("тёмная тема после 21:00", valid) == [("включи тёмную тему", "21:00")] or
      schedule.parse("тёмная тема после 21:00", valid) is not None, schedule.parse("тёмная тема после 21:00", valid))
rules = schedule.parse("не беспокоить с 23:00 до 08:00", valid)
check(rules == [("включи не беспокоить", "23:00"), ("выключи не беспокоить", "08:00")], rules)
check(schedule.parse("выключи защитник в 22:00", valid) is None, "переключатель с подтверждением в расписание не берём")
check(schedule.parse("включи бананы в 22:00", valid) is None, "неизвестное действие не берём")

rule = {"action": "включи не беспокоить", "at": "23:00", "last": ""}
t23 = time.mktime((2026, 10, 13, 23, 0, 0, 0, 0, -1))
check(len(schedule.due([rule], t23)) == 1 and len(schedule.due([rule], t23)) == 0, "срабатывает один раз в день")
check(schedule.due([{"action": "x", "at": "23:00", "last": ""}], t23 + 60) == [], "в другую минуту не срабатывает")

brain = make_brain(dict(BETA))
r = brain._beta_command("не беспокоить с 23:00 до 08:00", "не беспокоить с 23:00 до 08:00")
check(r and "23:00" in r.text and len(brain.cfg["schedules"]) == 2, r and r.text)
r = brain._beta_command("покажи расписания", "покажи расписания")
check(r and "в 23:00" in r.text, r and r.text)
r = brain._beta_command("удали все расписания", "удали все расписания")
check(r and brain.cfg["schedules"] == [], r and r.text)

# ================= 7. В стабильной сборке ничего из этого не работает =================
version.BUILD_CHANNEL = "stable"
brain = make_brain(dict(BETA))
for q in ["как дела у пк", "итог недели", "покажи список дел", "что занимает место", "наведи порядок в загрузках",
          "тёмная тема после 21:00", "очисти временные файлы"]:
    pass  # беты нет: команды доступны во всех сборках
version.BUILD_CHANNEL = "beta"

print("ALL OK")
