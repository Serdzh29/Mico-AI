"""Низкоуровневое управление Windows: клавиши, радиомодули (Wi-Fi/Bluetooth), реестр, звук, яркость,
питание, окна. Без внешних зависимостей, кроме pywin32 / (необязательно) pycaw."""
import ctypes, os, re, subprocess, time

NOWIN = 0x08000000  # CREATE_NO_WINDOW


def _user32():
    return ctypes.windll.user32


# ============================ PowerShell ============================
def ps(script, timeout=30):
    """Запуск PowerShell 5.1 (нужен для WinRT). Возвращает (ok, вывод)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                            "-Command", script], capture_output=True, text=True, errors="replace",
                           creationflags=NOWIN, timeout=timeout)
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, "таймаут"
    except Exception as e:
        return False, str(e)


# ============================ Клавиши ============================
VK = {"ctrl": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B, "tab": 0x09, "space": 0x20, "enter": 0x0D,
      "esc": 0x1B, "f4": 0x73, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
      "c": 0x43, "d": 0x44, "s": 0x53, "l": 0x4C, "h": 0x48, "v": 0x56, "a": 0x41, "n": 0x4E, "p": 0x50,
      "vol_up": 0xAF, "vol_down": 0xAE, "mute": 0xAD, "next": 0xB0, "prev": 0xB1, "stop": 0xB2, "play": 0xB3}
_EXT = {0x25, 0x26, 0x27, 0x28}


def press(*names, repeat=1):
    """Нажать комбинацию: press('win','ctrl','d')."""
    vks = [VK[n] for n in names]
    u = _user32()
    for _ in range(repeat):
        for v in vks:
            u.keybd_event(v, 0, 1 if v in _EXT else 0, 0)
        for v in reversed(vks):
            u.keybd_event(v, 0, (1 if v in _EXT else 0) | 2, 0)
        time.sleep(0.02)


# ============================ Реестр ============================
def reg_set(path, name, value, kind="dword", hive="HKCU"):
    import winreg
    h = getattr(winreg, "HKEY_CURRENT_USER" if hive == "HKCU" else "HKEY_LOCAL_MACHINE")
    k = winreg.CreateKeyEx(h, path, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(k, name, 0, winreg.REG_DWORD if kind == "dword" else winreg.REG_SZ, value)
    winreg.CloseKey(k)


def broadcast_setting(param="ImmersiveColorSet"):
    _user32().SendMessageTimeoutW(0xFFFF, 0x1A, 0, param, 2, 5000, None)


def shell_refresh():
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
EXPLORER_ADV = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
CONSENT = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\{}"


def set_theme(light):
    for n in ("AppsUseLightTheme", "SystemUsesLightTheme"):
        reg_set(PERSONALIZE, n, 1 if light else 0)
    broadcast_setting("ImmersiveColorSet")


# ============================ Wi-Fi / Bluetooth / режим полёта / хот-спот ============================
_WINRT = r"""
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask=([System.WindowsRuntimeSystemExtensions].GetMethods()|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'})[0]
function Await($op,$t){$m=$asTask.MakeGenericMethod($t);$task=$m.Invoke($null,@($op));$task.Wait(-1)|Out-Null;$task.Result}
"""

_RADIO = _WINRT + r"""
$null=[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]
$null=[Windows.Devices.Radios.RadioState,Windows.System.Devices,ContentType=WindowsRuntime]
$null=[Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime]
$null=Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) ([Windows.Devices.Radios.RadioAccessStatus])
$radios=Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
$kinds=@(@KINDS@); $found=0; $denied=0
foreach($r in $radios){ if($kinds -contains $r.Kind.ToString()){
  $found++; $res=Await ($r.SetStateAsync([Windows.Devices.Radios.RadioState]::@STATE@)) ([Windows.Devices.Radios.RadioAccessStatus])
  if($res.ToString() -ne 'Allowed'){$denied++} } }
Write-Output "FOUND=$found DENIED=$denied"
"""


def radio(kinds, on):
    """Включить/выключить радиомодули ('WiFi', 'Bluetooth', 'MobileBroadband'). Возвращает (ok, сообщение)."""
    script = (_RADIO.replace("@KINDS@", ",".join(f"'{k}'" for k in kinds))
              .replace("@STATE@", "On" if on else "Off"))
    ok, out = ps(script)
    m = re.search(r"FOUND=(\d+) DENIED=(\d+)", out)
    if not ok or not m:
        return False, out.splitlines()[-1] if out else "ошибка PowerShell"
    if m.group(1) == "0":
        return False, "такого адаптера в системе нет"
    if m.group(2) != "0":
        return False, "Windows запретила менять состояние (проверь «Параметры → Сеть и интернет»)"
    return True, ""


def airplane(on):
    return radio(["WiFi", "Bluetooth", "MobileBroadband"], not on)


def hotspot(on):
    script = _WINRT + r"""
$null=[Windows.Networking.Connectivity.NetworkInformation,Windows.Networking.Connectivity,ContentType=WindowsRuntime]
$null=[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime]
$p=[Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
if(-not $p){throw 'нет активного подключения к интернету'}
$m=[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($p)
if(@ON@){$op=$m.StartTetheringAsync()}else{$op=$m.StopTetheringAsync()}
$r=Await $op ([Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult])
Write-Output ("STATUS="+$r.Status.ToString())
""".replace("@ON@", "$true" if on else "$false")
    ok, out = ps(script, 40)
    m = re.search(r"STATUS=(\w+)", out)
    if ok and m and m.group(1) == "Success":
        return True, ""
    return False, (m.group(1) if m else (out.splitlines()[-1] if out else "ошибка"))


# ============================ Звук ============================
def _endpoint():
    import comtypes
    comtypes.CoInitialize()
    from pycaw.pycaw import AudioUtilities
    dev = AudioUtilities.GetSpeakers()
    ev = getattr(dev, "EndpointVolume", None)
    if ev is not None:                      # новые версии pycaw
        return ev
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume
    iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(iface, POINTER(IAudioEndpointVolume))


def get_volume():
    try:
        return round(_endpoint().GetMasterVolumeLevelScalar() * 100)
    except Exception:
        return None


def set_volume(pct):
    """Точная громкость 0–100. Возвращает итоговое значение или None, если pycaw недоступен."""
    try:
        pct = max(0, min(100, int(pct)))
        ep = _endpoint()
        ep.SetMasterVolumeLevelScalar(pct / 100.0, None)
        if pct > 0:
            ep.SetMute(0, None)
        return pct
    except Exception:
        return None


def change_volume(delta):
    cur = get_volume()
    if cur is not None:
        return set_volume(cur + delta)
    press("vol_up" if delta > 0 else "vol_down", repeat=max(1, abs(delta) // 2))   # 1 нажатие = 2%
    return None


def set_mute(mute):
    try:
        _endpoint().SetMute(1 if mute else 0, None)
    except Exception:
        press("mute")


# ============================ Яркость ============================
def get_brightness():
    ok, out = ps("(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness", 10)
    try:
        return int(out.split()[0]) if ok else None
    except (ValueError, IndexError):
        return None


def set_brightness(pct):
    pct = max(0, min(100, int(pct)))
    ok, _ = ps("(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods)"
               f".WmiSetBrightness(1,{pct})", 10)
    return pct if ok else None


# ============================ Питание ============================
PLANS = {"balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
         "performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
         "saver": "a1841308-3541-4fab-bc81-f71556f20b4a"}


def set_power_plan(key):
    r = subprocess.run(["powercfg", "/setactive", PLANS[key]], capture_output=True, creationflags=NOWIN)
    return r.returncode == 0


def run_quiet(*args):
    return subprocess.run(list(args), capture_output=True, creationflags=NOWIN).returncode == 0


def shutdown(restart=False, delay=10):
    return run_quiet("shutdown", "/r" if restart else "/s", "/t", str(delay), "/c", "Mico AI: по твоей команде")


def abort_shutdown():
    return run_quiet("shutdown", "/a")


def sleep_pc():
    subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], creationflags=NOWIN)


def hibernate():
    return run_quiet("shutdown", "/h")


def sign_out():
    return run_quiet("shutdown", "/l")


def lock():
    _user32().LockWorkStation()


def monitor_off():
    _user32().PostMessageW(0xFFFF, 0x0112, 0xF170, 2)


def empty_recycle_bin():
    ok, _ = ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue", 30)
    return ok


def swap_mouse_buttons(swap):
    _user32().SystemParametersInfoW(0x21, 1 if swap else 0, None, 3)


# ============================ Окна ============================
def _proc_name(pid):
    try:
        import psutil
        return psutil.Process(pid).name().lower()
    except Exception:
        return ""


def list_windows():
    """Видимые окна верхнего уровня (кроме окон самого Mico AI): [(hwnd, заголовок, процесс, класс)]."""
    import win32gui, win32process
    res, me = [], os.getpid()

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        if pid == me:
            return
        res.append((hwnd, title, _proc_name(pid), win32gui.GetClassName(hwnd)))
    win32gui.EnumWindows(cb, None)
    return res


def find_windows(tokens):
    """Окна, у которых имя процесса или заголовок содержат любой из токенов."""
    toks = [t.lower() for t in tokens if t]
    out = []
    for w in list_windows():
        hay_p, hay_t = w[2], w[1].lower()
        if w[2] == "explorer.exe" and w[3] != "CabinetWClass":      # не трогаем панель задач/рабочий стол
            continue
        if any(t in hay_p or t in hay_t for t in toks):
            out.append(w)
    return out


def focus(hwnd):
    import win32gui
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, 9)
        _user32().keybd_event(0x12, 0, 0, 0)          # «Alt» снимает запрет Windows на смену фокуса
        win32gui.SetForegroundWindow(hwnd)
        _user32().keybd_event(0x12, 0, 2, 0)
        return True
    except Exception:
        return False


def close_window(hwnd):
    _user32().PostMessageW(hwnd, 0x0010, 0, 0)       # WM_CLOSE — вежливо, программа сама спросит про сохранение


def show_window(hwnd, cmd):
    """cmd: 6 — свернуть, 3 — развернуть, 9 — восстановить."""
    import win32gui
    win32gui.ShowWindow(hwnd, cmd)


# ============================ Права администратора и системные компоненты ============================
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_elevated(cmdline, timeout=180):
    """Выполнить команду cmd с правами администратора. Если Mico AI не админ — Windows покажет запрос UAC.
    Возвращает (ok, сообщение). Команду не надо брать из пользовательского текста — только из таблицы компонентов."""
    if is_admin():
        try:
            r = subprocess.run(["cmd", "/c", cmdline], capture_output=True, text=True, errors="replace",
                               creationflags=NOWIN, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, "время ожидания вышло"
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, (out.splitlines()[-1] if out else "")
    arg = "/c " + cmdline
    esc = arg.replace("'", "''")
    script = (f"try {{ $p = Start-Process -FilePath cmd.exe -ArgumentList '{esc}' -Verb RunAs "
              f"-WindowStyle Hidden -PassThru -ErrorAction Stop; $p.WaitForExit(); exit $p.ExitCode }} "
              f"catch {{ Write-Output 'UAC_CANCEL'; exit 1 }}")
    ok, out = ps(script, timeout=timeout)
    if "UAC_CANCEL" in out:
        return False, "ты отказал в правах администратора"
    return ok, ("" if ok else (out.splitlines()[-1] if out else "код ошибки"))


def set_service(name, on):
    if on:
        return run_elevated(f"sc config {name} start= auto & sc start {name}")
    return run_elevated(f"sc stop {name} & sc config {name} start= disabled")


def set_feature(name, on):
    """Компонент Windows (Hyper-V, WSL…). Может потребовать перезагрузки."""
    if on:
        return run_elevated(f'powershell -NoProfile -Command "Enable-WindowsOptionalFeature -Online '
                            f'-FeatureName {name} -All -NoRestart"')
    return run_elevated(f'powershell -NoProfile -Command "Disable-WindowsOptionalFeature -Online '
                        f'-FeatureName {name} -NoRestart"')


def set_firewall(on):
    return run_elevated(f"netsh advfirewall set allprofiles state {'on' if on else 'off'}")


def set_defender_realtime(on):
    flag = "$false" if on else "$true"
    return run_elevated(f'powershell -NoProfile -Command "Set-MpPreference -DisableRealtimeMonitoring {flag}"')


def open_path(target):
    """Открыть программу/оснастку/страницу Windows (без параметров от пользователя)."""
    os.startfile(target)


def check_updates():
    """Запускает поиск обновлений Windows и открывает «Центр обновления»."""
    run_quiet("UsoClient.exe", "StartScan")
    try:
        os.startfile("ms-settings:windowsupdate")
    except Exception:
        pass
    return True, ""


# ============================ Переключатели и кнопки в «Параметрах» через UI Automation ============================
# Открывает страницу «Параметров» и находит элемент по названию (как его видит человек на экране):
# переключатель (mode='toggle'), кнопку (mode='click') или вариант-«радиокнопку» (mode='select').
# Названия передаёт только разработчик из таблицы компонентов — пользовательский текст сюда не попадает.
_UIA_SETTING = r"""
$ErrorActionPreference='SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$label='@LABEL@'; $mode='@MODE@'; $want=@WANT@
$root=[System.Windows.Automation.AutomationElement]::RootElement
$all=[System.Windows.Automation.Condition]::TrueCondition
$end=(Get-Date).AddSeconds(@TIMEOUT@)
function Match($el){ return ($el.Current.Name -eq $label) -or ($el.Current.Name -like "*$label*") }
while((Get-Date) -lt $end){
  foreach($w in $root.FindAll([System.Windows.Automation.TreeScope]::Children,$all)){
    if($w.Current.Name -notmatch '^(Параметры|Settings)'){continue}
    foreach($el in $w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$all)){
      $name=$el.Current.Name
      if($mode -eq 'select'){
        if($name -ne $label){continue}
        $p=$null
        if($el.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$p)){
          if($p.Current.IsSelected){ Write-Output 'ALREADY'; exit 0 }
          $p.Select(); Write-Output 'DONE'; exit 0 } }
      elseif($mode -eq 'click'){
        if($name -notlike "*$label*"){continue}
        $p=$null
        if($el.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$p)){
          $p.Invoke(); Write-Output 'DONE'; exit 0 } }
      else {
        # переключатель: сам элемент или строка (до трёх уровней вверх), в которой есть название
        $cand=$el; $ok=$false
        for($i=0;$i -lt 4 -and $cand -ne $null;$i++){ if(Match $cand){$ok=$true;break}; $cand=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($cand) }
        if(-not $ok){continue}
        $tp=$null
        if($el.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern,[ref]$tp)){
          $on = ($tp.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::On)
          if($on -eq $want){ Write-Output 'ALREADY'; exit 0 }
          $tp.Toggle(); Write-Output 'DONE'; exit 0 } }
    } } 
  Start-Sleep -Milliseconds 600 }
Write-Output 'NOTFOUND'
"""


def ui_setting(page, label, on=True, mode="toggle", timeout=14):
    """Открывает страницу «Параметров» (ms-settings:…) и переключает/нажимает элемент с названием label.
    Возвращает (ok, сообщение). Если элемент не нашёлся — (False, 'не нашёл …'), страница всё равно открыта."""
    try:
        os.startfile(page)
    except OSError as e:
        return False, f"не открылась страница ({e})"
    time.sleep(1.4)
    script = (_UIA_SETTING.replace("@LABEL@", label.replace("'", "''"))
              .replace("@MODE@", mode).replace("@WANT@", "$true" if on else "$false")
              .replace("@TIMEOUT@", str(timeout)))
    ok, out = ps(script, timeout + 15)
    out = out.strip().splitlines()[-1] if out.strip() else ""
    if out == "DONE":
        return True, ""
    if out == "ALREADY":
        return True, "уже было так"
    if out == "NOTFOUND":
        return False, f"открыл страницу, но переключатель «{label}» не нашёл — переключи его сам"
    return False, out or "ошибка UI Automation"



# ============================ Чтение и регулировка параметров ============================
def reg_get(path, name, default=None, hive="HKCU"):
    """Прочитать значение реестра (None/default, если его нет)."""
    import winreg
    h = getattr(winreg, "HKEY_CURRENT_USER" if hive == "HKCU" else "HKEY_LOCAL_MACHINE")
    try:
        k = winreg.OpenKey(h, path)
        v = winreg.QueryValueEx(k, name)[0]
        winreg.CloseKey(k)
        return v
    except OSError:
        return default


def _spi(action, value, update=3):
    """SystemParametersInfo с числовым значением: сразу применяет настройку, без перезагрузки."""
    return bool(_user32().SystemParametersInfoW(action, 0, ctypes.c_void_p(int(value)), update))


def set_mouse_speed(level):
    """Скорость указателя мыши, 1–20 (как ползунок в «Параметрах»; по умолчанию 10)."""
    level = max(1, min(20, int(level)))
    reg_set(r"Control Panel\Mouse", "MouseSensitivity", str(level), "str")
    return _spi(0x0071, level), ""


def set_mouse_precision(on):
    """Повышенная точность указателя (ускорение мыши)."""
    reg_set(r"Control Panel\Mouse", "MouseSpeed", "1" if on else "0", "str")
    arr = (ctypes.c_int * 3)(6, 10, 1) if on else (ctypes.c_int * 3)(0, 0, 0)
    _user32().SystemParametersInfoW(0x0004, 0, arr, 3)
    return True, ""


def set_wheel_lines(n):
    """Сколько строк прокручивать за одно движение колеса, 1–100 (по умолчанию 3)."""
    n = max(1, min(100, int(n)))
    reg_set(r"Control Panel\Desktop", "WheelScrollLines", str(n), "str")
    return _spi(0x0069, n), ""


def set_key_delay(level):
    """Задержка повтора символов: 0 — короткая, 3 — долгая."""
    level = max(0, min(3, int(level)))
    reg_set(r"Control Panel\Keyboard", "KeyboardDelay", str(level), "str")
    return _spi(0x0017, level), ""


def set_key_speed(level):
    """Частота повтора символов: 0 — медленно, 31 — быстро."""
    level = max(0, min(31, int(level)))
    reg_set(r"Control Panel\Keyboard", "KeyboardSpeed", str(level), "str")
    return _spi(0x000B, level), ""


def set_powercfg(key, minutes):
    """Таймеры питания: key — monitor-timeout / standby-timeout / hibernate-timeout; 0 — никогда."""
    m = max(0, int(minutes))
    ok1 = run_quiet("powercfg", "/change", f"{key}-ac", str(m))
    ok2 = run_quiet("powercfg", "/change", f"{key}-dc", str(m))
    return ok1 and ok2, "" if ok1 and ok2 else "powercfg не сработал"


# ============================ Выбор варианта из выпадающего списка (UI Automation) ============================
_UIA_CHOOSE = r"""
$ErrorActionPreference='SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$label='@LABEL@'; $option='@OPTION@'
$root=[System.Windows.Automation.AutomationElement]::RootElement
$all=[System.Windows.Automation.Condition]::TrueCondition
$end=(Get-Date).AddSeconds(14)
while((Get-Date) -lt $end){
  foreach($w in $root.FindAll([System.Windows.Automation.TreeScope]::Children,$all)){
    if($w.Current.Name -notmatch '^(Параметры|Settings)'){continue}
    foreach($el in $w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$all)){
      if($el.Current.Name -notlike "*$label*"){continue}
      $row=$el
      for($i=0;$i -lt 5 -and $row -ne $null;$i++){
        $ec=$null
        foreach($c in $row.FindAll([System.Windows.Automation.TreeScope]::Descendants,$all)){
          if($c.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$ec)){ break } }
        if($ec -ne $null){
          $ec.Expand(); Start-Sleep -Milliseconds 800
          foreach($o in $w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$all)){
            if($o.Current.Name -eq $option){
              $sp=$null; $ip=$null
              if($o.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$sp)){ $sp.Select(); Write-Output 'DONE'; exit 0 }
              if($o.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$ip)){ $ip.Invoke(); Write-Output 'DONE'; exit 0 } } }
          Write-Output 'NOOPTION'; exit 0 }
        $row=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($row) } }
  }
  Start-Sleep -Milliseconds 600 }
Write-Output 'NOTFOUND'
"""


def ui_choose(page, label, option, timeout=14):
    """Открывает страницу «Параметров», раскрывает выпадающий список с названием label и выбирает option."""
    try:
        os.startfile(page)
    except OSError as e:
        return False, f"не открылась страница ({e})"
    time.sleep(1.4)
    script = (_UIA_CHOOSE.replace("@LABEL@", label.replace("'", "''"))
              .replace("@OPTION@", option.replace("'", "''")))
    ok, out = ps(script, timeout + 15)
    out = out.strip().splitlines()[-1] if out.strip() else ""
    if out == "DONE":
        return True, ""
    if out == "NOOPTION":
        return False, f"в списке «{label}» нет варианта «{option}»"
    if out == "NOTFOUND":
        return False, f"открыл страницу, но список «{label}» не нашёл — выбери сам"
    return False, out or "ошибка UI Automation"


# ============================ Параметры, которые проще менять через реестр или shell ============================
def classic_context_menu(on):
    """Классическое контекстное меню Windows 11 (полное, со старыми пунктами). Включается созданием ключа COM-класса."""
    key = r"HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"
    if on:
        ok = run_quiet("reg", "delete", key, "/f")
        ok = run_quiet("reg", "add", key + r"\InprocServer32", "/ve", "/f") or ok
        return ok, "" if ok else "Windows не дала изменить реестр"
    ok = run_quiet("reg", "delete", key, "/f")
    return ok, "" if ok else "ключ уже был удалён"


def restart_explorer():
    run_quiet("taskkill", "/f", "/im", "explorer.exe")
    subprocess.Popen(["explorer.exe"], creationflags=NOWIN)
    return True, ""


# ============================ Рабочее место и история копирования (бета) ============================
def visible_apps():
    """Программы с видимыми окнами: [{'proc', 'exe', 'title'}]. Окна самого Mico AI не считаются."""
    import win32gui, win32process, psutil
    me, res = os.getpid(), []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
            return
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        if pid == me:
            return
        try:
            p = psutil.Process(pid)
            res.append({"proc": p.name().lower(), "exe": p.exe(), "title": win32gui.GetWindowText(hwnd)})
        except psutil.Error:
            pass
    win32gui.EnumWindows(cb, None)
    return res


def running_names():
    """Имена всех запущенных процессов в нижнем регистре: чтобы не открывать дважды то, что уже открыто."""
    import psutil
    return {(p.info.get("name") or "").lower() for p in psutil.process_iter(["name"])}


def process_of(hwnd):
    """Имя процесса окна (для истории копирования: из менеджеров паролей не сохраняем)."""
    import win32process, psutil
    try:
        return psutil.Process(win32process.GetWindowThreadProcessId(hwnd)[1]).name().lower()
    except Exception:
        return ""


def launch(exe):
    """Открывает программу, которую пользователь подтвердил. Без прав администратора."""
    subprocess.Popen([exe], close_fds=True, creationflags=NOWIN)
    return True


# ============================ Здоровье ПК, диски (бета) ============================
def disk_usage(path):
    import shutil
    return shutil.disk_usage(path)


def boot_time():
    import psutil
    return psutil.boot_time()


def defender_on():
    """Защита Windows в реальном времени: True / False / None (не удалось узнать)."""
    ok, out = ps("(Get-MpComputerStatus).RealTimeProtectionEnabled", 15)
    if not ok:
        return None
    word = out.strip().split()[-1].lower() if out.strip() else ""
    return {"true": True, "false": False}.get(word)
