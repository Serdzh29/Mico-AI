"""Автозапуск Mico AI при входе в Windows.

Используется ключ HKCU\\...\\Run: программа стартует с обычными правами пользователя и не требует повышения.
Задача Планировщика с наивысшими правами давала ошибку 0x800702E4 («операция требует повышения»), поэтому её больше
не создаём. Старую задачу удаляем при установке и при первом запуске (repair_if_outdated)."""
import os
import subprocess
import sys

TASK = "Mico"                                             # имя старой задачи Планировщика (только для уборки)
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOWIN = 0x08000000
FROZEN = bool(getattr(sys, "frozen", False))              # собран в Mico.exe (PyInstaller)
HERE = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))


def pythonw():
    exe = sys.executable
    cand = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return cand if os.path.exists(cand) else exe


def command(script=None, exe=None):
    """Строка, которую Windows запустит при входе: программа и признак «запущено из автозапуска»."""
    if FROZEN:
        return f'"{exe or sys.executable}" --autostart'
    script = os.path.abspath(script or os.path.join(HERE, "main.py"))
    return f'"{pythonw()}" "{script}" --autostart'


def _set_run_value(cmd):
    import winreg
    k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(k, "Mico", 0, winreg.REG_SZ, cmd)


def _get_run_value():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        return winreg.QueryValueEx(k, "Mico")[0]
    except (ImportError, OSError):
        return None


def _delete_run_value():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(k, "Mico")
    except (ImportError, OSError):
        pass


def _task_exists():
    """Осталась ли старая задача Планировщика от прошлых версий."""
    r = subprocess.run(["schtasks", "/Query", "/TN", TASK], capture_output=True, text=True,
                       errors="replace", creationflags=NOWIN)
    return r.returncode == 0


def _delete_task():
    subprocess.run(["schtasks", "/Delete", "/TN", TASK, "/F"], capture_output=True, text=True,
                   errors="replace", creationflags=NOWIN)


def install(script=None, exe=None):
    """Включает автозапуск. Возвращает (ok, сообщение). Права администратора не нужны."""
    try:
        _set_run_value(command(script=script, exe=exe))
    except (ImportError, OSError) as e:
        return False, f"Не получилось включить автозапуск: {e}"
    if _task_exists():
        _delete_task()                                  # старая задача не должна стартовать Mico AI второй раз
    return True, "Автозапуск включён: Mico AI стартует при входе в Windows"


def status():
    """(включён ли, путь к запускаемому файлу или None) — по тому, что реально записано в Windows."""
    cmd = _get_run_value()
    if cmd is None and _task_exists():
        return True, None                               # старая задача ещё стоит — починится при запуске
    if cmd is None:
        return False, None
    cmd = str(cmd).strip()
    path = cmd.split('"')[1] if cmd.startswith('"') and cmd.count('"') >= 2 else cmd.split()[0]
    return True, path


def remove():
    """Выключает автозапуск. Если ничего не было — это тоже успех: состояние уже нужное."""
    _delete_run_value()
    if _task_exists():
        _delete_task()
    return True, "Автозапуск выключен"


def repair_if_outdated():
    """Старые версии создавали задачу в Планировщике. Переносим автозапуск на ключ Run."""
    if not _task_exists():
        return False
    return install()[0]
