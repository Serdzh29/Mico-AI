"""Рабочее место (бета): запомнить открытые программы и открыть их снова по команде.
Mico AI открывает только программы, которые сам видел на экране, и только после твоего «да».
Здесь только логика. Окна и запуск программ — в winctl.py, подтверждение — в brain.py."""
import os, re, time

SKIP = {"explorer.exe", "shellexperiencehost.exe", "searchhost.exe", "startmenuexperiencehost.exe",
        "textinputhost.exe", "applicationframehost.exe", "systemsettings.exe", "runtimebroker.exe",
        "sihost.exe", "taskmgr.exe", "lockapp.exe", "mico.exe", "python.exe", "pythonw.exe"}
MAX_APPS = 8
SAVE = re.compile(r"^(?:запомни|сохрани|запомнить|сохранить)\s+(?:моё\s+|мое\s+)?рабочее место$")
RESTORE = re.compile(r"^(?:восстанови|открой|верни|вернуть|восстановить)\s+(?:моё\s+|мое\s+)?рабочее место$")


def command(ql):
    s = (ql or "").strip(" .!?")
    if SAVE.match(s):
        return "save"
    if RESTORE.match(s):
        return "restore"
    return None


def pick(windows):
    """windows: [{'proc', 'exe', 'title'}]. Возвращает уникальные программы, которые есть на диске, до MAX_APPS."""
    seen, out = set(), []
    for w in windows:
        proc, exe = (w.get("proc") or "").lower(), w.get("exe") or ""
        if not proc or proc in SKIP or proc in seen:
            continue
        if not os.path.isfile(exe):
            continue
        seen.add(proc)
        out.append({"proc": proc, "exe": exe})
        if len(out) >= MAX_APPS:
            break
    return out


def save(cfg, windows, now=None):
    apps = pick(windows)
    cfg["workspace"] = {"saved_at": now or time.time(), "apps": apps}
    return apps


def saved_apps(cfg):
    return list((cfg.get("workspace") or {}).get("apps", []))


def plan_restore(cfg, running):
    """Что открыть: сохранённые программы, которых сейчас нет среди запущенных (running — имена в нижнем регистре)."""
    return [a for a in saved_apps(cfg) if a["proc"] not in running and os.path.isfile(a["exe"])]


def names(apps):
    return ", ".join(os.path.splitext(a["proc"])[0] for a in apps)
