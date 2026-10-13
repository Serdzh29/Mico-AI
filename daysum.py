"""Итог дня (бета): сколько времени провёл за компьютером и в каких программах.
Берёт журнал окон за сегодня. Ничего не отправляет и не пишет в журнал сам."""
import re, time

SKIP = {"explorer.exe", "lockapp.exe", "shellexperiencehost.exe", "searchhost.exe", "mico.exe", "python.exe", "pythonw.exe"}
MIN_SEG = 5                    # сек: короче не считаем (промелькнувшие окна)
TODAY = re.compile(r"^(?:итог\w*\s+дня|итоги\s+дня|что\s+я\s+делал\s+сегодня|как\s+прошёл\s+день|как\s+прошел\s+день)$")
SCHEDULE = re.compile(r"присылай\s+итог\w*\s+(?:дня\s+)?в\s+(\d{1,2})[:.](\d{2})")


def command(ql):
    """('today', None) | ('schedule', 'HH:MM') | None."""
    s = (ql or "").strip(" .!?")
    if TODAY.match(s):
        return ("today", None)
    if re.search(r"не\s+присылай\s+итог", s):
        return ("schedule", "")                       # выключить ежевечерний итог
    m = SCHEDULE.search(s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if 0 <= hh < 24 and 0 <= mm < 60:
            return ("schedule", f"{hh:02d}:{mm:02d}")
    return None


def day_start(now):
    t = time.localtime(now)
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


def summarize(events, t0, t1):
    """events: [(start, end, proc, title)]. Возвращает (всего секунд, [(программа, секунд)] по убыванию)."""
    per, total = {}, 0
    for s, e, proc, _title in events:
        d = min(e, t1) - max(s, t0)
        if d < MIN_SEG:
            continue
        p = (proc or "").lower() or "?"
        if p in SKIP:
            continue
        per[p] = per.get(p, 0) + d
        total += d
    return total, sorted(per.items(), key=lambda kv: -kv[1])[:5]


def fmt(seconds):
    m = int(seconds) // 60
    h, m = divmod(m, 60)
    return f"{h} ч {m:02d} мин" if h else f"{m} мин"


def text(total, top):
    if total < MIN_SEG:
        return "Сегодня записей пока нет: за компьютером я ещё ничего не видел."
    head = f"Сегодня за компьютером: {fmt(total)}."
    if not top:
        return head
    parts = ", ".join(f"{p.rsplit('.', 1)[0] if p.endswith('.exe') else p} — {fmt(s)}" for p, s in top[:3])
    return f"{head} Больше всего времени: {parts}."


def build(store, now):
    total, top = summarize(store.between(day_start(now), now), day_start(now), now)
    return text(total, top)


def due(now, cfg):
    """Пора ли прислать итог: время из cfg['day_summary_at'] прошло, а сегодня ещё не присылали."""
    at = cfg.get("day_summary_at") or ""
    if not re.fullmatch(r"\d{2}:\d{2}", at):
        return False
    t = time.localtime(now)
    hh, mm = map(int, at.split(":"))
    today = time.strftime("%Y-%m-%d", t)
    if (t.tm_hour, t.tm_min) < (hh, mm) or cfg.get("day_summary_last") == today:
        return False
    cfg["day_summary_last"] = today
    return True


WEEK = re.compile(r"^итог\w*\s+недели$|^что\s+я\s+делал\s+на\s+этой\s+неделе$")


def week_command(ql):
    return bool(WEEK.match((ql or "").strip(" .!?")))


def week_text(store, now):
    """Сколько времени ушло за последние 7 дней: по дням и по программам."""
    start = day_start(now) - 6 * 86400
    events = store.between(start, now)
    per_day, per_app, total = {}, {}, 0
    for s, e, proc, _t in events:
        d = min(e, now) - max(s, start)
        p = (proc or "").lower() or "?"
        if d < MIN_SEG or p in SKIP:
            continue
        day = time.strftime("%d.%m", time.localtime(max(s, start)))
        per_day[day] = per_day.get(day, 0) + d
        per_app[p] = per_app.get(p, 0) + d
        total += d
    if total < MIN_SEG:
        return "За неделю записей пока нет."
    best = max(per_day.items(), key=lambda kv: kv[1])
    top = sorted(per_app.items(), key=lambda kv: -kv[1])[:3]
    apps = ", ".join(f"{p.rsplit('.', 1)[0] if p.endswith('.exe') else p} — {fmt(s)}" for p, s in top)
    return (f"За 7 дней за компьютером: {fmt(total)}. Больше всего — {best[0]} ({fmt(best[1])}). "
            f"Чаще всего: {apps}.")
