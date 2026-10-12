"""Автозапуск Mico: задача в Планировщике Windows. Срабатывает при входе в систему и при разблокировке,
каждый раз запускает Mico заново (старый экземпляр сам завершается — см. main.py, «один экземпляр»)."""
import os, subprocess, sys
from xml.sax.saxutils import escape

TASK = "Mico"
NOWIN = 0x08000000
FROZEN = bool(getattr(sys, "frozen", False))          # собран в Mico.exe (PyInstaller)
HERE = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))


def pythonw():
    exe = sys.executable
    cand = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return cand if os.path.exists(cand) else exe


def task_xml(user, exe, args, workdir):
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Mico AI: запускается при входе в Windows и при разблокировке экрана</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{escape(user)}</UserId>
    </LogonTrigger>
    <SessionStateChangeTrigger>
      <Enabled>true</Enabled>
      <StateChange>SessionUnlock</StateChange>
      <UserId>{escape(user)}</UserId>
    </SessionStateChangeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{escape(user)}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>Parallel</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(exe)}</Command>
      <Arguments>{escape(args)}</Arguments>
      <WorkingDirectory>{escape(workdir)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
'''


def _user():
    dom, name = os.environ.get("USERDOMAIN", ""), os.environ.get("USERNAME", "")
    return f"{dom}\\{name}" if dom and name else name or "CurrentUser"


def install(script=None, exe=None):
    """Создаёт задачу. Возвращает (ok, сообщение). Права администратора не нужны."""
    if FROZEN:
        exe, args, workdir = exe or sys.executable, "--autostart", os.path.dirname(exe or sys.executable)
    else:
        script = os.path.abspath(script or os.path.join(HERE, "main.py"))
        exe, args, workdir = pythonw(), f'"{script}" --autostart', os.path.dirname(script)
    xml_path = os.path.join(os.environ.get("APPDATA", HERE), "Mico", "mico_task.xml")
    os.makedirs(os.path.dirname(xml_path), exist_ok=True)
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(task_xml(_user(), exe, args, workdir))
    # старый вариант автозапуска (ключ Run) убираем, чтобы Mico не стартовал дважды
    _remove_run_key()
    r = subprocess.run(["schtasks", "/Create", "/TN", TASK, "/XML", xml_path, "/F"],
                       capture_output=True, text=True, errors="replace", creationflags=NOWIN)
    out = (r.stdout + r.stderr).strip()
    return r.returncode == 0, ("Автозапуск включён: при входе в Windows и при разблокировке" if r.returncode == 0
                               else f"Не получилось создать задачу: {out}")


def remove():
    r = subprocess.run(["schtasks", "/Delete", "/TN", TASK, "/F"], capture_output=True, text=True,
                       errors="replace", creationflags=NOWIN)
    _remove_run_key()
    return r.returncode == 0, ("Автозапуск выключен" if r.returncode == 0 else "Задачи не было")


def _remove_run_key():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                           winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(k, "Mico")
        except FileNotFoundError:
            pass
    except (ImportError, OSError):
        pass
