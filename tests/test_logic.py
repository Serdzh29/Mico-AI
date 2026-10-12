import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, time, types
sys.path.insert(0, ROOT)
import memory as M, context as X

# ---- context ----
calls = []
X.remember("media", repeat=lambda: calls.append("next") or "r", undo=lambda: calls.append("prev"))
assert X.is_repeat("Дальше!") and X.is_repeat("ещё") and X.is_undo("назад")
assert not X.is_repeat("открой ютуб")
print("context repeat/undo words ok, last kind:", X.last()["kind"])
X.clear(); assert X.last() is None
X.remember("x"); X._last["at"] = time.time() - 9999
assert X.last() is None; print("context TTL ok")

# ---- memory with fake store ----
class FakeStore:
    def __init__(self, rows, acts=()):
        self.rows, self.acts = rows, list(acts)
    def between(self, t0, t1):
        return [r for r in self.rows if r[1] >= t0 and r[0] <= t1]
    def actions_between(self, t0, t1):
        return [(ts, t) for ts, t in self.acts if t0 <= ts <= t1]

now = time.time()
def day_at(d, h, m):           # локальное время «d дней назад, h:m»
    lt = time.localtime(now - d * 86400)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, m, 0, 0, 0, -1))
y = 1
rows = [
    (day_at(y, 9, 0), day_at(y, 10, 0), "chrome.exe", "Habr — статьи"),
    (day_at(y, 10, 0), day_at(y, 11, 30), "code.exe", "main.py - Mico"),
    (day_at(y, 17, 0), day_at(y, 17, 40), "telegram.exe", "[скрыто]"),
    (day_at(y, 18, 0), day_at(y, 18, 20), "chrome.exe", "Рецепт борща — YouTube"),
]
st = FakeStore(rows)
r = M.yesterday_recap(st, now)
print("recap:", M.recap_text(r))
assert r["last_proc"] == "Chrome" and "борща" in r["last_title"]
assert r["top"][0][0] == "Chrome" or r["top"][0][0] == "VS Code"

# привычки: 3 дня подряд в этот час открывали Telegram и просили «открой телеграм»
h_now = time.localtime(now).tm_hour
hour_ts = lambda d: time.mktime(time.localtime(now - d * 86400)[:3] + (h_now, 5, 0, 0, 0, -1))
rows2 = [(hour_ts(d), hour_ts(d) + 600, "telegram.exe", "Чат") for d in (1, 2, 3)]
acts = [(hour_ts(d), "открой телеграм") for d in (1, 2, 3)]
print("pretty:", M.pretty("TELEGRAM.exe"), M.pretty("foo.exe"))
