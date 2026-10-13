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

# ---------- автозапуск: задача в Планировщике — источник правды ----------
calls = []
xml_state = {"exists": False, "cmd": r"C:\Mico AI Github\Mico.exe"}

class _R:
    def __init__(self, rc, out=""):
        self.returncode, self.stdout, self.stderr = rc, out, ""

def fake_run(args, **kw):
    calls.append(args)
    if args[:2] == ["schtasks", "/Query"]:
        if not xml_state["exists"]:
            return _R(1, "ERROR: не найдено")
        return _R(0, f"<Task><Actions><Exec><Command>{xml_state['cmd']}</Command></Exec></Actions></Task>")
    if args[:2] == ["schtasks", "/Create"]:
        xml_state["exists"] = True
        return _R(0, "SUCCESS")
    if args[:2] == ["schtasks", "/Delete"]:
        if not xml_state["exists"]:
            return _R(1, "ERROR")
        xml_state["exists"] = False
        return _R(0, "SUCCESS")
    return _R(0)

A.subprocess.run = fake_run

on, cmd = A.status()
check(on is False and cmd is None, "задачи нет — выключено")

ok, msg = A.install(exe=r"C:\Mico AI Github\Mico.exe")
check(ok and xml_state["exists"], msg)
xml = open(_os.path.join(_tmp, "Mico", "mico_task.xml"), encoding="utf-16").read()
check("<Delay>PT10S</Delay>" in xml, "задержка после входа")
check("SessionUnlock" in xml and "LogonTrigger" in xml, "запуск при входе и разблокировке")
check("<RunLevel>HighestAvailable</RunLevel>" in xml, "задача стартует с наивысшими правами пользователя (иначе падает с 0x800702E4)")
check(A.status()[0] is True, "после установки задача видна")

# выключение задачи, которой нет, — не ошибка (раньше здесь было предупреждение)
ok, _ = A.remove()
check(ok and not xml_state["exists"], "выключили")
ok, msg = A.remove()
check(ok, "повторное выключение — тоже успех: " + msg)

# установка повторно перезаписывает задачу (чинит старый путь к exe)
xml_state.update(exists=True, cmd=r"C:\Старое\Mico.exe")
ok, _ = A.install(exe=r"C:\Mico AI Github\Mico.exe")
check(ok and any(c[:2] == ["schtasks", "/Create"] for c in calls), "install всегда пересоздаёт задачу")

print("ALL OK")
