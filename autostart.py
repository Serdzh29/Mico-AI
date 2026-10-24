"""Автозапуск Mico AI при входе в Windows.

Используется ключ HKCU\\...\\Run: программа стартует с обычными правами пользователя и не требует повышения.
Задача Планировщика с наивысшими правами давала ошибку 0x800702E4 («операция требует повышения»), поэтому её больше
не создаём. Старую задачу удаляем при установке и при первом запуске (repair_if_outdated)."""
import os
import subprocess
import sys

TASK = "Mico"                                             # имя старой задачи Планировщика (только для уборки)
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# Windows отдельно хранит, разрешён ли пункт автозагрузки (его переключают Диспетчер задач и Параметры → Автозагрузка).
# Если там стоит «Отключено», программа в Run есть, но при входе в Windows не стартует — поэтому проверяем и это.
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
APPROVED_ON = bytes([0x02]) + bytes(11)     # 02 00 ... — разрешено
APPROVED_OFF = bytes([0x03]) + bytes(11)    # 03 00 ... — отключено пользователем
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


def _approved():
    """True — Windows разрешает запуск (записи нет или она «включено»); False — пользователь отключил Mico."""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0, winreg.KEY_READ)
        data = winreg.QueryValueEx(k, "Mico")[0]
    except (ImportError, OSError):
        return True
    return not (isinstance(data, (bytes, bytearray)) and len(data) > 0 and data[0] & 1)


def _set_approved(on):
    """Записывает «разрешено/отключено» так же, как Диспетчер задач. Без прав администратора."""
    try:
        import winreg
        k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, "Mico", 0, winreg.REG_BINARY, APPROVED_ON if on else APPROVED_OFF)
    except (ImportError, OSError):
        pass


def _clear_approved():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(k, "Mico")
    except (ImportError, OSError):
        pass


def _path_of(cmd):
    """Путь к программе из строки автозапуска (кавычки вокруг пути необязательны)."""
    cmd = str(cmd).strip()
    return cmd.split('"')[1] if cmd.startswith('"') and cmd.count('"') >= 2 else cmd.split()[0]


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
    _set_approved(True)                                 # снимаем «Отключено», если его поставили в Диспетчере задач
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
    path = _path_of(cmd)
    if not _approved():
        return False, path                              # Windows отключил пункт: в настройках показываем «выключено»
    return True, path


def remove():
    """Выключает автозапуск. Если ничего не было — это тоже успех: состояние уже нужное."""
    _delete_run_value()
    _clear_approved()
    if _task_exists():
        _delete_task()
    return True, "Автозапуск выключен"


def repair_if_outdated():
    """Чинит автозапуск при старте: переносит старую задачу Планировщика на ключ Run и обновляет путь,
    если программа переехала (переустановили в другую папку, exe удалили)."""
    if _task_exists():
        return install()[0]
    cmd = _get_run_value()
    if cmd is not None and FROZEN:
        path = _path_of(cmd)
        if path and not os.path.exists(path):
            return install()[0]
    return False
