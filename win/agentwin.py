"""Windows-часть режима агента: читает активное окно, нажимает кнопки и вводит текст.
Работает только на Windows. Скрипты PowerShell здесь фиксированные: параметры (названия кнопок, текст)
передаются в base64, поэтому текст из ответа модели никогда не попадает в код скрипта.
Чистая логика (что можно, что нужно подтвердить) — в agent.py."""
import base64, json, time

from win import agent

_SNAP = r"""
$ErrorActionPreference='SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$types=@('Button','MenuItem','Hyperlink','CheckBox','RadioButton','TabItem','ListItem','ComboBox','Edit','Document')
$cs=@(); foreach($t in $types){ $cs += New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::$t) }
$cond=New-Object System.Windows.Automation.OrCondition(,[System.Windows.Automation.Condition[]]$cs)
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]@HWND@)
$els=$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cond)
$btn=New-Object System.Collections.ArrayList; $fld=New-Object System.Collections.ArrayList; $n=0
foreach($e in $els){
  $n++; if($n -gt 3000){break}
  $name=$e.Current.Name; if(-not $name){continue}
  $ct=$e.Current.ControlType.ProgrammaticName
  if($ct -in 'ControlType.Button','ControlType.MenuItem','ControlType.Hyperlink','ControlType.CheckBox','ControlType.RadioButton','ControlType.TabItem','ControlType.ListItem','ControlType.ComboBox'){ [void]$btn.Add($name) }
  elseif($ct -in 'ControlType.Edit','ControlType.Document'){ [void]$fld.Add($name) }
}
$pw=$false
$foc=[System.Windows.Automation.AutomationElement]::FocusedElement
if($foc -ne $null){ $pw=[bool]$foc.Current.IsPassword }
[pscustomobject]@{ buttons=@($btn | Select-Object -First 60); fields=@($fld | Select-Object -First 30); password=$pw } | ConvertTo-Json -Compress | ForEach-Object { [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($_)) }
"""

_CLICK = r"""
$ErrorActionPreference='SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$types=@('Button','MenuItem','Hyperlink','CheckBox','RadioButton','TabItem','ListItem','ComboBox','Edit','Document')
$cs=@(); foreach($t in $types){ $cs += New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::$t) }
$cond=New-Object System.Windows.Automation.OrCondition(,[System.Windows.Automation.Condition[]]$cs)
$want=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('@NAME@'))
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]@HWND@)
$els=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cond))
$hit=$null
foreach($pass in 1,2){
  foreach($e in $els){
    $ct=$e.Current.ControlType.ProgrammaticName
    if($ct -notin 'ControlType.Button','ControlType.MenuItem','ControlType.Hyperlink','ControlType.CheckBox','ControlType.RadioButton','ControlType.TabItem','ControlType.ListItem','ControlType.ComboBox'){continue}
    $nm=$e.Current.Name
    if($pass -eq 1){ $ok = ($nm -eq $want) } else { $ok = ($nm.IndexOf($want,[StringComparison]::OrdinalIgnoreCase) -ge 0) }
    if($ok){ $hit=$e; break }
  }
  if($hit -ne $null){ break }
}
if($hit -eq $null){ Write-Output 'NOTFOUND'; exit 0 }
$p=$null
if($hit.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$p)){ $p.Invoke(); Write-Output 'DONE'; exit 0 }
if($hit.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern,[ref]$p)){ $p.Toggle(); Write-Output 'DONE'; exit 0 }
if($hit.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$p)){ $p.Select(); Write-Output 'DONE'; exit 0 }
if($hit.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$p)){ $p.Expand(); Write-Output 'DONE'; exit 0 }
$r=$hit.Current.BoundingRectangle   # окно не отдаёт паттерны нажатия (часто на Qt) — жмём по центру элемента
if($r.Width -gt 0 -and $r.Height -gt 0){
  Add-Type -AssemblyName System.Windows.Forms,System.Drawing
  Add-Type -MemberDefinition '[DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint d,System.IntPtr i);' -Name U -Namespace N
  $x=[int]($r.X+$r.Width/2); $y=[int]($r.Y+$r.Height/2)
  $prev=[System.Windows.Forms.Cursor]::Position
  [System.Windows.Forms.Cursor]::Position=New-Object System.Drawing.Point($x,$y)
  Start-Sleep -Milliseconds 150
  [N.U]::mouse_event(0x0002,0,0,0,[IntPtr]::Zero)
  Start-Sleep -Milliseconds 80
  [N.U]::mouse_event(0x0004,0,0,0,[IntPtr]::Zero)
  Start-Sleep -Milliseconds 120
  [System.Windows.Forms.Cursor]::Position=$prev
  Write-Output 'DONE'; exit 0
}
Write-Output 'NOTCLICKABLE'
"""

_FILL = r"""
$ErrorActionPreference='SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$types=@('Button','MenuItem','Hyperlink','CheckBox','RadioButton','TabItem','ListItem','ComboBox','Edit','Document')
$cs=@(); foreach($t in $types){ $cs += New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::$t) }
$cond=New-Object System.Windows.Automation.OrCondition(,[System.Windows.Automation.Condition[]]$cs)
Add-Type -AssemblyName System.Windows.Forms
$want=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('@NAME@'))
$text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('@TEXT@'))
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]@HWND@)
$els=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cond))
$hit=$null
foreach($pass in 1,2){
  foreach($e in $els){
    $ct=$e.Current.ControlType.ProgrammaticName
    if($ct -notin 'ControlType.Edit','ControlType.Document','ControlType.ComboBox'){continue}
    $nm=[string]$e.Current.Name
    if($pass -eq 1){ $ok = ($nm -eq $want) } else { $ok = ($nm.IndexOf($want,[StringComparison]::OrdinalIgnoreCase) -ge 0) }
    if($ok){ $hit=$e; break }
  }
  if($hit -ne $null){ break }
}
if($hit -eq $null){ Write-Output 'NOTFOUND'; exit 0 }
$vp=$null
if($hit.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$vp) -and -not $vp.Current.IsReadOnly){
  $vp.SetValue($text); Write-Output 'DONE'; exit 0 }
$hit.SetFocus(); Start-Sleep -Milliseconds 150
[System.Windows.Forms.SendKeys]::SendWait('^a')
@UNI@
[UniKey]::Send($text)
Write-Output 'DONE'
"""

_SENDKEYS = r"""
$ErrorActionPreference='SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms
$keys=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('@KEYS@'))
[System.Windows.Forms.SendKeys]::SendWait($keys)
Write-Output 'DONE'
"""


_UNI = r"""
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public static class UniKey {
  [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Explicit)] public struct U { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; }
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public U u; }
  [DllImport("user32.dll", SetLastError=true)] static extern uint SendInput(uint n, INPUT[] i, int size);
  public static void Send(string s) {
    foreach (char c in s) {
      INPUT[] a = new INPUT[2];
      for (int k = 0; k < 2; k++) {
        a[k].type = 1;
        if (c == '\n') { a[k].u.ki.wVk = 0x0D; } else { a[k].u.ki.wScan = c; a[k].u.ki.dwFlags = 0x0004; }
        if (k == 1) a[k].u.ki.dwFlags |= 0x0002;
      }
      SendInput(2, a, Marshal.SizeOf(typeof(INPUT)));
      System.Threading.Thread.Sleep(6);
    }
  }
}
'@
"""

_TYPE = r"""
$ErrorActionPreference='SilentlyContinue'
@UNI@
$text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('@TEXT@'))
[UniKey]::Send($text)
Write-Output 'DONE'
""".replace("@UNI@", _UNI)


_FILL = _FILL.replace("@UNI@", _UNI)


def _b64(s):
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


# Русские названия, которых нет в заголовке или имени процесса окна
APP_ALIASES = {"ватсап": "whatsapp", "вотсап": "whatsapp", "ватсапп": "whatsapp", "вацап": "whatsapp",
               "макс": "max.exe", "тимс": "teams", "тимз": "teams", "телеграмм": "telegram"}


def window_tokens(name):
    """Что искать среди окон по названию программы: «телеграм» → telegram, «ватсап» → whatsapp."""
    from win import commands
    low = " ".join(str(name or "").lower().replace("ё", "е").split()).strip(" .!?")
    toks = [v for k, v in APP_ALIASES.items() if k == low or k in low.split()]
    try:
        toks += commands._app_tokens(low)
    except Exception:
        pass
    toks.append(low)
    seen, out = set(), []
    for t in toks:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


class WinDriver:

    """Драйвер для agent.Runner. Все вызовы блокирующие — выполняются в фоновом потоке агента.
    fallback() — окно, с которым пользователь работал до Mico: если сейчас на переднем плане сам Mico
    (пользователь пишет в чате), действуем именно в нём, а не в собственном окне."""

    def __init__(self, fallback=lambda: None, notify=None):
        self.fallback = fallback
        self.notify = notify or (lambda t: None)

    def _foreground(self):
        import os
        import win32gui, win32process
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and win32process.GetWindowThreadProcessId(hwnd)[1] == os.getpid():
            alt = self.fallback()
            if alt and win32gui.IsWindow(alt):
                hwnd = alt
        return hwnd, (win32gui.GetWindowText(hwnd) or "").strip()

    def snapshot(self):
        from win import system as winctl
        try:
            hwnd, title = self._foreground()
        except Exception:
            return {"title": "", "buttons": [], "fields": [], "password": False}
        ok, out = winctl.ps(_SNAP.replace("@HWND@", str(int(hwnd))), 25)
        data = {}
        if ok and out.strip():
            try:
                data = json.loads(base64.b64decode(out.strip().splitlines()[-1]).decode("utf-8"))   # PowerShell отдаёт cp866, Python читал cp1251: передаём base64 от UTF-8
            except ValueError:
                data = {}
        return {"title": title, "buttons": _as_list(data.get("buttons")),
                "fields": _as_list(data.get("fields")), "password": bool(data.get("password"))}

    def do(self, name, args):
        from win import system as winctl
        if name == agent.LAUNCH:
            from win import commands
            from win import messenger as msgr
            r = commands.handle(f"открой {args['name']}", self.notify, self.fallback)
            # «Не нашёл: «X»» приходит обычным ответом, а не None: раньше агент считал такую программу открытой
            # и печатал текст в первое попавшееся окно
            ok = r is not None and not str(r.text or "").startswith("Не нашёл")
            msg = (r.text if r else "") if ok else f"не нашёл программу «{args['name']}»"
            if not ok:
                # установки «для себя» (Telegram, MAX, WhatsApp, Discord) — их нет в PATH
                for path in msgr.launch_paths(args["name"]):
                    try:
                        import subprocess
                        subprocess.Popen([path])
                        ok, msg = True, ""
                        break
                    except Exception as e:
                        msg = str(e)
            time.sleep(2.5)                                       # окну нужно время, чтобы появиться
            found = winctl.find_windows(window_tokens(args["name"]))
            if found:
                winctl.focus(found[0][0])
            return ok, msg
        if name == agent.WAIT:
            time.sleep(args["sec"])
            return True, ""
        if name == agent.FOCUS:
            found = winctl.find_windows(window_tokens(args["title"]))
            if not found:
                return False, f"нет открытого окна «{args['title']}»"
            winctl.focus(found[0][0])
            time.sleep(0.5)
            return True, ""
        hwnd, _ = self._foreground()
        if name == agent.CLICK:
            ok, out = winctl.ps(_CLICK.replace("@NAME@", _b64(args["name"])).replace("@HWND@", str(int(hwnd))), 20)
            result = (out.strip().splitlines() or [""])[-1] if ok else "ERROR"
            reasons = {"NOTFOUND": "такой кнопки нет в окне", "NOTCLICKABLE": "кнопка не нажимается",
                       "ERROR": "ошибка UI Automation"}
            return result == "DONE", reasons.get(result, "")
        if name == agent.FILL:
            ok, out = winctl.ps(_FILL.replace("@NAME@", _b64(args["field"])).replace("@TEXT@", _b64(args["text"]))
                                .replace("@HWND@", str(int(hwnd))), 30)
            result = (out.strip().splitlines() or [""])[-1] if ok else "ERROR"
            reasons = {"NOTFOUND": "такого поля в окне нет", "ERROR": "ошибка UI Automation"}
            return result == "DONE", reasons.get(result, "")
        if name == agent.TYPE:
            winctl.focus(hwnd)
            ok, _ = winctl.ps(_TYPE.replace("@TEXT@", _b64(args["text"])), 30)   # SendInput + UNICODE: кириллица без SendKeys
            return ok, "" if ok else "не получилось ввести текст"
        if name == agent.PRESS:
            winctl.focus(hwnd)
            ok, _ = winctl.ps(_SENDKEYS.replace("@KEYS@", _b64(agent.KEY_MAP[args["key"]])), 20)
            return ok, "" if ok else "не получилось нажать клавишу"
        return False, f"неизвестное действие {name}"


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return [str(x) for x in v]
