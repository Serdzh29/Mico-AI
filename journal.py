"""Таймлайн дня (WI): программы по времени, реплики и копии в одной ленте. Только расчёты, без Qt.
Титулы окон и тексты копий не показываем — только время, программа и размер."""
import daysum

MERGE_GAP = 60            # сек: если программа снова открылась через минуту — это один отрезок
PALETTE = ["#9BE3A8", "#9FD3FF", "#FFCFA3", "#D6B8FF", "#FFA94D", "#FF9F9F", "#A8E6E0", "#F6E58D"]
SNIPPET = 70


def colour_for(name):
    """Одна и та же программа всегда одного цвета."""
    return PALETTE[sum(ord(c) for c in str(name)) % len(PALETTE)]


def _clip(text, n=SNIPPET):
    s = " ".join(str(text or "").split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def rows(events, chats, clips, t0, t1):
    """Лента дня: список dict {ts, kind, label, detail, secs, colour, share}, по времени.
    events — [(start, end, process, title)], chats — [(ts, role, text)], clips — [(ts, text)]."""
    apps = []
    for s, e, proc, _title in sorted(events, key=lambda x: x[0]):
        s, e = max(s, t0), min(e, t1)
        d = e - s
        p = (proc or "").lower() or "?"
        if d < daysum.MIN_SEG or p in daysum.SKIP:
            continue
        if apps and apps[-1]["name"] == p and s - apps[-1]["end"] <= MERGE_GAP:
            apps[-1]["end"] = max(apps[-1]["end"], e)
            apps[-1]["secs"] += d
            continue
        apps.append({"name": p, "ts": s, "end": e, "secs": d})
    total = sum(a["secs"] for a in apps) or 1
    out = []
    for a in apps:
        name = a["name"][:-4] if a["name"].endswith(".exe") else a["name"]
        out.append({"ts": a["ts"], "kind": "app", "label": name, "detail": daysum.fmt(a["secs"]),
                    "secs": a["secs"], "colour": colour_for(a["name"]), "share": a["secs"] / total})
    for ts, role, text in chats:
        if t0 <= ts < t1:
            who = "Ты" if role == "user" else "Mico"
            out.append({"ts": ts, "kind": "chat", "label": who, "detail": _clip(text), "secs": 0,
                        "colour": "", "share": 0})
    for ts, text in clips:
        if t0 <= ts < t1:
            out.append({"ts": ts, "kind": "copy", "label": "Копия", "detail": f"{len(str(text or ''))} знаков",
                        "secs": 0, "colour": "", "share": 0})
    return sorted(out, key=lambda r: r["ts"])


def summary(lst):
    """Одна строка над лентой: сколько времени за компьютером и сколько разговоров."""
    secs = sum(r["secs"] for r in lst if r["kind"] == "app")
    talks = sum(1 for r in lst if r["kind"] == "chat")
    if not secs:
        return "За компьютером пока ничего не записано."
    return f"За компьютером {daysum.fmt(secs)}, разговоров: {talks}."


def hour_line(lst):
    """Сводка за последний час для мини-сводки перед перерывом: три самые долгие программы и число разговоров."""
    per = {}
    for r in lst:
        if r["kind"] == "app":
            per[r["label"]] = per.get(r["label"], 0) + r["secs"]
    if not per:
        return "За последний час записей нет."
    top = sorted(per.items(), key=lambda kv: -kv[1])[:3]
    text = "За последний час: " + ", ".join(f"{n} — {daysum.fmt(s)}" for n, s in top) + "."
    talks = sum(1 for r in lst if r["kind"] == "chat")
    return text + (f" Разговоров: {talks}." if talks else "")
