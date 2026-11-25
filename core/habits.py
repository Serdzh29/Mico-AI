"""Привычки пользователя на ПК: какие программы он чаще всего держит открытыми и какие команды
просит у Mico в это время дня. По ним при открытии чата сразу предлагаются быстрые действия.
Чистая логика без Qt и Windows (проверяется в tests/test_habits.py). Данные берутся из локального
журнала активности (data/tracker.py) и никуда не отправляются."""
import math
import time

DAYS = 14                 # смотрим последние две недели
HALF_LIFE_DAYS = 4        # вчерашнее важнее недельной давности
MIN_SECONDS = 60          # программа, открытая меньше двух минут за всё время, — не привычка

# системные окна Windows и сам Mico — не предлагаем «открыть» их
SKIP = {"explorer.exe", "searchhost.exe", "searchapp.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
        "lockapp.exe", "applicationframehost.exe", "textinputhost.exe", "conhost.exe", "dwm.exe", "mico.exe",
        "python.exe", "pythonw.exe", "taskmgr.exe", "rundll32.exe", "consent.exe", "sihost.exe", "ctfmon.exe",
        "systemsettings.exe", "shellhost.exe", "widgets.exe", "msedgewebview2.exe"}

NAMES = {"chrome.exe": "Chrome", "msedge.exe": "Edge", "firefox.exe": "Firefox", "opera.exe": "Opera",
         "browser.exe": "Яндекс Браузер", "telegram.exe": "Telegram", "discord.exe": "Discord",
         "steam.exe": "Steam", "code.exe": "VS Code", "winword.exe": "Word", "excel.exe": "Excel",
         "powerpnt.exe": "PowerPoint", "outlook.exe": "Outlook", "spotify.exe": "Spotify", "notepad.exe": "Блокнот",
         "obs64.exe": "OBS", "vlc.exe": "VLC", "zoom.exe": "Zoom", "ms-teams.exe": "Teams", "teams.exe": "Teams",
         "whatsapp.exe": "WhatsApp", "photoshop.exe": "Photoshop", "figma.exe": "Figma", "notion.exe": "Notion",
         "windowsterminal.exe": "Терминал", "pycharm64.exe": "PyCharm", "yandexmusic.exe": "Яндекс Музыка"}


def app_label(process):
    """Понятное имя программы по имени процесса. None — программу не предлагаем."""
    p = str(process or "").strip().lower()
    if not p or p in SKIP:
        return None
    if p in NAMES:
        return NAMES[p]
    base = p[:-4] if p.endswith(".exe") else p
    if not base or not any(ch.isalpha() for ch in base):
        return None
    return base[:1].upper() + base[1:]


def app_usage(rows, now=None, days=DAYS, blocked=()):
    """rows — записи журнала (start, end, process, title). Возвращает {process: вес}:
    сколько секунд человек работал в программе, свежие дни весят больше, а текущий час суток — ещё больше.
    Заблокированные в настройках программы (blocked) не учитываются."""
    now = time.time() if now is None else now
    hour = time.localtime(now).tm_hour
    blocked = [str(b).lower() for b in (blocked or ())]
    total, weight = {}, {}
    for row in rows or ():
        try:
            start, end, process = float(row[0]), float(row[1]), str(row[2]).lower()
        except (TypeError, ValueError, IndexError):
            continue
        secs = max(0.0, end - start)
        if not secs or now - end > days * 86400 or app_label(process) is None:
            continue
        if any(b and b in process for b in blocked):
            continue
        age_days = max(0.0, (now - end) / 86400.0)
        k = 0.5 ** (age_days / HALF_LIFE_DAYS)
        h = time.localtime(start).tm_hour
        if min(abs(h - hour), 24 - abs(h - hour)) <= 1:      # в это же время дня — важнее
            k *= 2.0
        total[process] = total.get(process, 0.0) + secs
        weight[process] = weight.get(process, 0.0) + secs * k
    return {p: w for p, w in weight.items() if total[p] >= MIN_SECONDS}


def top_apps(usage, n=2):
    """Самые частые программы: список (process, имя), без повторов имени."""
    out, seen = [], set()
    for p, _w in sorted((usage or {}).items(), key=lambda kv: (-kv[1], kv[0])):
        name = app_label(p)
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append((p, name))
        if len(out) >= n:
            break
    return out


def note_command(cfg, chip_id, now=None):
    """Запоминает, в какой час и когда последний раз человек просил команду."""
    now = time.time() if now is None else now
    hours = cfg.setdefault("chip_hours", {}).setdefault(chip_id, [0] * 24)
    if len(hours) != 24:
        hours[:] = [0] * 24
    hours[time.localtime(now).tm_hour] += 1
    cfg.setdefault("chip_last", {})[chip_id] = int(now)


def command_score(cfg, chip_id, now=None):
    """Насколько команда подходит прямо сейчас: сколько раз её просили, просят ли её в это время
    дня и давно ли просили в последний раз. Без данных о часах — просто число нажатий."""
    now = time.time() if now is None else now
    count = float((cfg.get("chip_usage") or {}).get(chip_id, 0))
    if count <= 0:
        return 0.0
    score = count
    hours = (cfg.get("chip_hours") or {}).get(chip_id)
    if hours and len(hours) == 24:
        h = time.localtime(now).tm_hour
        near = hours[h] + 0.5 * (hours[(h - 1) % 24] + hours[(h + 1) % 24])
        score += 2.0 * near                               # в это время дня её просят чаще
    last = (cfg.get("chip_last") or {}).get(chip_id)
    if last:
        age_days = max(0.0, (now - float(last)) / 86400.0)
        score *= 0.5 + 0.5 * (0.5 ** (age_days / HALF_LIFE_DAYS))   # давно не просили — вес плавно меньше
    return score
