"""Ответ о создателе Mico и автозапуск через Планировщик. Без Windows: системные вызовы подменены."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types, tempfile
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
_tmp = tempfile.mkdtemp()
_os.environ["APPDATA"] = _tmp

import identity
import autostart as A

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

# ---------- создатель ----------
for q in ["кто тебя создал?", "кто твой создатель?", "кто тебя придумал?", "кто тебя сделал",
          "кто твой автор", "кем ты создан?", "кто тебя разработал", "кто тебя написал?", "кто ты создал"]:
    r = identity.answer(q)
    check(r is not None and "Serdzh Kozhe" in r.text, (q, r and r.text))
for q in ["кто придумал пиццу", "кто твой любимый автор книги", "какая погода", "создай таймер на 5 минут",
          "кто выиграл чемпионат", "расскажи про Serdzh Kozhe"]:
    check(identity.answer(q) is None, q)
check(identity.answer("кто тебя создал?").mood == "happy")

# ---------- автозапуск: ключ Run (без повышения прав); старая задача Планировщика — только уборка ----------
run_value = {"cmd": None}
tasks = {"exists": False, "deleted": 0}
A._set_run_value = lambda cmd: run_value.update(cmd=cmd)
A._get_run_value = lambda: run_value["cmd"]
A._delete_run_value = lambda: run_value.update(cmd=None)
A._task_exists = lambda: tasks["exists"]
A._delete_task = lambda: (tasks.update(exists=False), tasks.__setitem__("deleted", tasks["deleted"] + 1))

on, path = A.status()
check(on is False and path is None, "ничего не включено — выключено")

ok, msg = A.install(exe=r"C:\Mico AI Github\Mico.exe")
check(ok, msg)
check(run_value["cmd"].endswith('main.py" --autostart') and run_value["cmd"].startswith('"'), run_value["cmd"])
check(A.status()[0] is True, A.status())
check("HighestAvailable" not in open(A.__file__, encoding="utf-8").read(), "наивысших прав нигде нет")

# миграция: была старая задача Планировщика — установка её убирает, автозапуск остаётся один
run_value["cmd"] = None
tasks.update(exists=True)
on, _ = A.status()
check(on is True, "старая задача считается включённым автозапуском (и починится)")
check(A.repair_if_outdated() is True and tasks["exists"] is False and run_value["cmd"] is not None,
      "repair переносит автозапуск на ключ Run и убирает задачу")
check(A.repair_if_outdated() is False, "без старой задачи ремонт ничего не делает")

ok, _ = A.remove()
check(ok and run_value["cmd"] is None and A.status()[0] is False, "выключили")
ok, msg = A.remove()
check(ok, "повторное выключение — тоже успех: " + msg)

print("ALL OK")
