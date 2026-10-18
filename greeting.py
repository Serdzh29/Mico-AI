"""Что Mico AI показывает при включении ПК. Пользователь выбирает до 3 пунктов в ⚙ Настройки → Умное.
Каждый пункт — либо готовый текст сразу, либо фоновая задача (сеть, обновления)."""
import os, re, time
from collections import defaultdict

import psutil

import memory
import reminders
import weather
import winctl
from memory import pretty

MAX_ITEMS = 3
ITEMS = [
    ("date", "📅 Дата и дни до выходных"),
    ("recap", "🕐 Итог вчерашнего дня и незаконченное"),
    ("system", "💻 Состояние ПК: батарея, диск, перезагрузка"),
    ("reminders", "⏰ Напоминания на сегодня"),
    ("updates", "🔄 Обновления Windows"),
    ("routine", "🌅 Утренняя рутина: что обычно открываешь"),
    ("weather", "🌤 Погода"),
]
LABELS = dict(ITEMS)
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября",
          "ноября", "декабря"]


def date_text(now=None):
    lt = time.localtime(now or time.time())
    wd = lt.tm_wday                                   # 0 — понедельник
    if wd >= 5:
        tail = "Сегодня выходной."
    else:
        tail = f"До выходных {5 - wd} дн."
    return f"Сегодня {WEEKDAYS[wd]}, {lt.tm_mday} {MONTHS[lt.tm_mon - 1]}. {tail}"


def system_text():
    parts = []
    try:
        b = psutil.sensors_battery()
    except Exception:
        b = None
    if b is not None:
        note = " — подключи зарядку" if b.percent < 20 and not b.power_plugged else ""
        parts.append(f"заряд {b.percent:.0f}%{note}")
    drive = os.environ.get("SystemDrive", "C:") + "\\"
    try:
        free_gb = psutil.disk_usage(drive).free / 2 ** 30
        parts.append(f"свободно на {drive[:2]} {free_gb:.0f} ГБ" + (" — мало места" if free_gb < 10 else ""))
    except OSError:
        pass
    try:
        days = (time.time() - psutil.boot_time()) / 86400
        if days > 7:
            parts.append(f"ПК не перезагружался {days:.0f} дн. — стоит перезагрузить")
    except Exception:
        pass
    if not parts:
        return ""
    return "Состояние ПК: " + "; ".join(parts) + "."


def reminders_text():
    items = reminders.today()
    if not items:
        return "На сегодня напоминаний нет."
    lines = [f"{time.strftime('%H:%M', time.localtime(i['due']))} {i['text']}" for i in items[:5]]
    return "Сегодня: " + "; ".join(lines) + "."


def routine_text(store, now=None, days=14, min_days=3):
    """Что человек обычно открывает утром (6–11 часов)."""
    now = now or time.time()
    seen = defaultdict(set)
    for s, e, p, t in store.between(now - days * 86400, now):
        if e - s < 120:
            continue
        if 6 <= time.localtime(s).tm_hour < 11:
            seen[pretty(p)].add(time.strftime("%Y%m%d", time.localtime(s)))
    top = [n for n, d in sorted(seen.items(), key=lambda kv: -len(kv[1])) if len(d) >= min_days][:3]
    if not top:
        return None
    return "Утром ты обычно работаешь в: " + ", ".join(top) + ". Открыть?"


def updates_job():
    ok, out = winctl.ps("$s=New-Object -ComObject Microsoft.Update.Session;"
                        "$r=$s.CreateUpdateSearcher().Search(\"IsInstalled=0 and Type='Software' and IsHidden=0\");"
                        "Write-Output ('UPD=' + $r.Updates.Count)", timeout=180)
    m = re.search(r"UPD=(\d+)", out)
    if not ok or not m:
        return None
    n = int(m.group(1))
    return "Обновлений Windows нет." if n == 0 else f"Есть обновления Windows: {n}. Установить можно в «Центре обновления»."


def plan(ids, cfg, store):
    """(готовые тексты, фоновые задачи). Фоновая задача возвращает текст или None."""
    ids = [i for i in ids if i in LABELS][:MAX_ITEMS]
    sync, jobs = [], []
    for i in ids:
        if i == "date":
            sync.append(date_text())
        elif i == "recap" and cfg.get("memory_on", True):
            r = memory.recap_text(memory.yesterday_recap(store))
            if r:
                sync.append(r)
        elif i == "system":
            s = system_text()
            if s:
                sync.append(s)
        elif i == "reminders":
            sync.append(reminders_text())
        elif i == "routine":
            r = routine_text(store)
            if r:
                sync.append(r)
        elif i == "updates":
            jobs.append(updates_job)
        elif i == "weather" and cfg.get("weather_on", True):
            jobs.append(lambda: _weather_line(cfg))
    return sync, jobs


def _weather_line(cfg):
    txt, err = weather.get_weather(cfg)
    return "🌤 " + txt if txt else f"Погоду пока не узнал: {err}"
