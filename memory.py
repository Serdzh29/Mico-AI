"""Память: рекап вчерашнего дня, «на чём остановился», и подсказки по привычкам.
Опирается на зашифрованный журнал Store (окна/время) и журнал команд (actions)."""
import time
from collections import Counter

BLOCK_TITLE = "[скрыто]"
PRETTY = {"chrome.exe": "Chrome", "msedge.exe": "Edge", "firefox.exe": "Firefox", "telegram.exe": "Telegram",
          "discord.exe": "Discord", "code.exe": "VS Code", "explorer.exe": "Проводник", "steam.exe": "Steam",
          "winword.exe": "Word", "excel.exe": "Excel", "powerpnt.exe": "PowerPoint", "notepad.exe": "Блокнот",
          "spotify.exe": "Spotify", "yandex.exe": "Яндекс Браузер", "opera.exe": "Opera", "vlc.exe": "VLC"}


def pretty(proc):
    p = (proc or "").lower()
    if p in PRETTY:
        return PRETTY[p]
    return p[:-4] if p.endswith(".exe") else p


def _day_start(ts):
    lt = time.localtime(ts)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def yesterday_recap(store, now=None):
    now = now or time.time()
    today0 = _day_start(now)
    y0 = today0 - 86400
    rows = [r for r in store.between(y0, today0) if r[1] - r[0] >= 30]
    if not rows:
        return None
    totals = Counter()
    for s, e, p, t in rows:
        totals[p] += min(e, today0) - max(s, y0)
    top = [(pretty(p), int(secs)) for p, secs in totals.most_common(3) if secs >= 60]
    named = [r for r in rows if r[3] != BLOCK_TITLE and r[3]]
    last = named[-1] if named else rows[-1]
    return {"top": top, "last_proc": pretty(last[2]), "last_title": last[3][:70],
            "last_time": time.strftime("%H:%M", time.localtime(last[1]))}


def recap_text(r):
    if not r:
        return None
    parts = []
    if r["top"]:
        names = ", ".join(f"{n} ({s // 60} мин)" if s < 3600 else f"{n} ({s // 3600} ч {s % 3600 // 60} мин)"
                          for n, s in r["top"])
        parts.append(f"Вчера больше всего времени ушло на: {names}.")
    parts.append(f"Ты остановился на «{r['last_title']}» ({r['last_proc']}) около {r['last_time']}.")
    return " ".join(parts)

