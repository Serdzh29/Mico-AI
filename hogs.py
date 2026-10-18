"""Что тормозит компьютер: самые прожорливые программы. Закрываем только по подтверждению и вежливо —
через окно (WM_CLOSE), программа сама спросит про несохранённое. Системные процессы не трогаем никогда."""
import os, re, time

PHRASE = re.compile(
    r"^(?:что\s+(?:сейчас\s+)?(?:тормозит|грузит|жрёт|жрет|нагружает|съедает)\w*"
    r"(?:\s+(?:компьютер\w*|ноутбук\w*|пк|систем\w*|процессор\w*|память|озу))?"
    r"|кто\s+(?:сейчас\s+)?(?:грузит|тормозит|жрёт|жрет)\w*(?:\s+(?:процессор\w*|память|озу))?"
    r"|почему\s+(?:компьютер\w*|ноутбук\w*|пк)?\s*(?:тормозит|медленно\w*|лагает))$")

# Процессы, которые нельзя трогать ни при каких условиях: система, оболочка, сама Mico AI.
PROTECTED = {
    "system", "system idle process", "registry", "memory compression", "idle",
    "explorer.exe", "dwm.exe", "svchost.exe", "csrss.exe", "winlogon.exe", "lsass.exe", "services.exe",
    "wininit.exe", "smss.exe", "fontdrvhost.exe", "sihost.exe", "taskhostw.exe", "audiodg.exe",
    "msmpeng.exe", "runtimebroker.exe", "searchhost.exe", "startmenuexperiencehost.exe",
    "shellexperiencehost.exe", "textinputhost.exe", "ctfmon.exe", "conhost.exe", "spoolsv.exe",
    "python.exe", "pythonw.exe", "mico.exe", "dllhost.exe", "wudfhost.exe",
}
CPU_MIN = 15          # % всего процессора
MEM_MIN = 800 * 1024 * 1024   # байт: от 800 МБ памяти уже заметно


def command(ql):
    return bool(PHRASE.match((ql or "").strip(" .!?").replace("ё", "е")))


def is_protected(name, pid=None):
    return (name or "").lower() in PROTECTED or pid in (None, 0, 4, os.getpid())


def pick(samples, limit=3):
    """samples: [{'name', 'pid', 'cpu' (% всего ПК), 'mem' (байт)}]. Возвращает самые заметные, без системных."""
    rows = [s for s in samples if not is_protected(s.get("name"), s.get("pid"))
            and (s.get("cpu", 0) >= CPU_MIN or s.get("mem", 0) >= MEM_MIN)]
    rows.sort(key=lambda s: (-s.get("cpu", 0), -s.get("mem", 0)))
    return rows[:limit]


def describe(s):
    return f"{s['name']}: процессор {s.get('cpu', 0):.0f}%, память {s.get('mem', 0) / 1024 ** 3:.1f} ГБ"


def sample(wait=1.0):
    """Нагрузка по программам за короткий промежуток. Только чтение."""
    import psutil
    procs = []
    for p in psutil.process_iter(["name"]):
        try:
            p.cpu_percent(None)
            procs.append(p)
        except psutil.Error:
            pass
    time.sleep(wait)
    cores = psutil.cpu_count() or 1
    out = []
    for p in procs:
        try:
            out.append({"name": p.info.get("name") or p.name(), "pid": p.pid,
                        "cpu": p.cpu_percent(None) / cores, "mem": p.memory_info().rss})
        except psutil.Error:
            continue
    return out


def windows_of(pid):
    """Видимые окна верхнего уровня этого процесса: [hwnd]."""
    import win32gui, win32process
    found = []

    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
            found.append(hwnd)
    win32gui.EnumWindows(cb, None)
    return found


def close_gently(pid):
    """Просит окна закрыться (WM_CLOSE). Возвращает число окон, которым отправили запрос. 0 — окон нет."""
    import winctl
    hwnds = windows_of(pid)
    for h in hwnds:
        winctl.close_window(h)
    return len(hwnds)
