"""Сравнение сборок Windows 11 по проверенным данным (data/windows_releases.json).

Отвечает только для Windows 11 и только для версий, которые Microsoft ещё поддерживает
(срок зависит от редакции: Home и Pro или Enterprise и Education). Сборки, которых нет в данных,
не выдумывает: говорит, что знает и на какую дату данные проверены."""
import datetime
import json
import os
import re
import sys

FILE = os.path.join(getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__)),
                    "data", "windows_releases.json")
TOKEN = re.compile(r"\b(\d{5}(?:\.\d+)?|\d{2}h\d)\b", re.IGNORECASE)
WIN10 = re.compile(r"windows\s*10|виндовс\s*10|винд\w*\s*10|\bwin\s*10\b", re.IGNORECASE)
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]
CHANNELS = {"release": "стабильная", "release_preview": "Release Preview",
            "beta": "Beta", "experimental": "Experimental"}
GROUP_TEXT = {"home_pro": "Home и Pro", "enterprise": "Enterprise и Education"}


def load(path=FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _date(text):
    return datetime.date.fromisoformat(text) if text else None


def _ru(d):
    return f"{d.day} {MONTHS[d.month - 1]} {d.year} года"


def _key(build):
    """'26300.9457' → (26300, 9457): сравнение сборок по номеру."""
    a, _, b = str(build).partition(".")
    return int(a), int(b or 0)


def find_tokens(text):
    return [m.group(1) for m in TOKEN.finditer(text or "")]


def is_windows10(text):
    return bool(WIN10.search(text or ""))


def edition_group(edition_id):
    """Какой срок поддержки применяется: Enterprise/Education или Home/Pro (по умолчанию)."""
    e = (edition_id or "").lower()
    return "enterprise" if e.startswith(("enterprise", "education", "iotenterprise")) else "home_pro"


def lifecycle_of(version, data):
    for rec in data["lifecycle"]:
        if rec["version"].lower() == str(version).lower():
            return rec
    return None


def support(version, group, data, today):
    """('supported' | 'ended' | 'unknown', дата окончания или None)."""
    rec = lifecycle_of(version, data)
    if rec is None:
        return "unknown", None
    end = _date(rec.get("home_pro_end" if group == "home_pro" else "enterprise_end"))
    if end is None:                       # срок не указан: версия выпущена — поддерживается
        return ("supported" if rec.get("released") else "unknown"), None
    return ("supported" if today <= end else "ended"), end


def version_of(build, data):
    """Версия по номеру сборки: точное совпадение или та же основная сборка (26300.xxxx → 26H2)."""
    key = _key(build)
    for b in data["builds"]:
        if _key(b["build"]) == key:
            return b["version"]
    for b in data["builds"]:
        if _key(b["build"])[0] == key[0]:
            return b["version"]
    return None


def resolve(token, data):
    """Токен → {'build', 'version', 'known'}; None — токен не распознан.
    '26h2' → лучшая проверенная сборка версии (стабильная, иначе самая новая).
    '26300.9457' → сборка; если её нет в данных, known=False, версия берётся по основному номеру."""
    t = token.lower()
    if re.fullmatch(r"\d{2}h\d", t):
        cands = [b for b in data["builds"] if b["version"].lower() == t]
        if not cands:
            return None
        pool = [b for b in cands if b.get("channel") == "release"] or cands
        best = max(pool, key=lambda b: _key(b["build"]))
        return {"build": best["build"], "version": best["version"], "known": True}
    if re.fullmatch(r"\d{5}(\.\d+)?", t):
        exact = next((b for b in data["builds"] if _key(b["build"]) == _key(t)), None)
        if exact:
            return {"build": exact["build"], "version": exact["version"], "known": True}
        return {"build": t, "version": version_of(t, data), "known": False}
    return None


def _checked(data):
    return _ru(_date(data["checked"]))


def _refusal(version, group, end):
    return (f"Windows 11 {version} уже не поддерживается Microsoft: для редакций {GROUP_TEXT[group]} "
            f"поддержка закончилась {_ru(end)}. Поэтому сравнивать её не буду. "
            "Обновись до поддерживаемой версии, например 25H2 или 26H2.")


def _problem(ref, group, data, today):
    """None — сравнивать можно; иначе текст, почему нельзя."""
    if ref["version"] is None:
        return (f"Сборка {ref['build']} не относится к Windows 11, которую я знаю. "
                "Сравниваю только Windows 11.")
    status, end = support(ref["version"], group, data, today)
    if status == "ended":
        return _refusal(ref["version"], group, end)
    if status == "unknown":
        return f"Windows 11 {ref['version']} нет в моих данных о поддержке, поэтому сравнивать её не буду."
    return None


def _support_line(version, group, today, data):
    _, end = support(version, group, data, today)
    if end is None:
        return (f"Поддержка для {GROUP_TEXT[group]}: действует. "
                "Точная дата окончания в моих данных пока не проверена.")
    days = (end - today).days
    if days == 0:
        left = ", заканчивается сегодня"
    elif days == 1:
        left = ", заканчивается завтра"
    elif days <= 60:
        left = f", осталось {days} дн"
    else:
        left = ""
    return f"Поддержка для {GROUP_TEXT[group]}: до {_ru(end)}{left}."


def _line(build):
    tag = "" if build.get("tier", "official") == "official" else ", по сторонним данным, не Microsoft"
    return f"{build.get('version')}, сборка {build['build']} ({CHANNELS.get(build.get('channel'), 'проверено')}{tag})"


def _describe(build):
    """Что известно о сборке — список строк."""
    if build.get("highlights"):
        return [f"• {_line(build)}:"] + [f"    – {h}" for h in build["highlights"]]
    return [f"• {_line(build)}: проверенного списка изменений нет — см. журнал обновлений Microsoft."]


def compare(a_token, b_token, data, group="home_pro", today=None):
    today = today or datetime.date.today()
    ra, rb = resolve(a_token, data), resolve(b_token, data)
    if ra is None or rb is None:
        missing = a_token if ra is None else b_token
        return (f"Не знаю сборку или версию «{missing}». Сравниваю Windows 11 по моим проверенным данным: "
                + ", ".join(sorted({b["version"] for b in data["builds"]})) + ".")
    for ref in (ra, rb):
        if not ref["known"]:
            return (f"Сборки {ref['build']} нет в моих проверенных данных (они на {_checked(data)}). "
                    "Могу сравнить только известные сборки.")
        problem = _problem(ref, group, data, today)
        if problem:
            return problem
    lo, hi = sorted([ra, rb], key=lambda r: _key(r["build"]))
    rows = sorted((b for b in data["builds"] if _key(lo["build"]) < _key(b["build"]) <= _key(hi["build"])),
                  key=lambda b: _key(b["build"]))
    lines = [f"{lo['build']} → {hi['build']} (данные проверены {_checked(data)}):"]
    if not rows:
        lines.append("Между этими сборками в моих данных ничего нет.")
    for b in rows:
        lines += _describe(b)
    sources = sorted({b["source"] for b in rows if b.get("source") and b.get("highlights")})
    if sources:
        lines.append("Источники: " + "; ".join(sources) + ".")
    return "\n".join(lines)


def previous(build, data):
    """Ближайшая проверенная сборка Windows 11 ниже указанной."""
    cur = _key(build)
    below = [b for b in data["builds"] if _key(b["build"]) < cur and _key(b["build"])[0] >= 22000]
    return max(below, key=lambda b: _key(b["build"])) if below else None


def current(system, data, today=None):
    """Отчёт о сборке этого ПК: версия, поддержка, отличия от предыдущей сборки."""
    today = today or datetime.date.today()
    build = system.get("build")
    if not build:
        return "Не смог узнать сборку Windows на этом ПК."
    if build < 22000:
        return "На этом ПК Windows 10. Я сравниваю только Windows 11, здесь помочь не смогу."
    full = f"{build}.{system['ubr']}" if system.get("ubr") is not None else str(build)
    group = edition_group(system.get("edition"))
    ref = resolve(full, data)
    edition = system.get("edition") or "редакция не определена"
    if ref["version"] is None:
        return f"Сборка {full} мне не знакома, поэтому не могу сказать, какая это версия Windows 11."
    head = f"Сейчас у тебя Windows 11 {ref['version']}, сборка {full} ({edition})."
    status, end = support(ref["version"], group, data, today)
    if status == "ended":
        return head + "\n" + _refusal(ref["version"], group, end)
    lines = [head, _support_line(ref["version"], group, today, data)]
    prev = previous(full, data)
    if not ref["known"]:
        lines.append(f"Этой сборки нет в моих проверенных данных (они на {_checked(data)}).")
        if prev:
            lines.append(f"Ближайшая проверенная сборка ниже — {prev['build']}:")
            lines += _describe(prev)
        return "\n".join(lines)
    if prev is None:
        lines.append("Более ранней проверенной сборки Windows 11 в моих данных нет.")
    else:
        lines.append("Что изменилось по сравнению с предыдущей проверенной сборкой:")
        lines.append(compare(prev["build"], full, data, group, today))
    return "\n".join(lines)


def read_system():
    """Сборка, UBR и редакция этого ПК из реестра. Вне Windows или при ошибке — пустые значения."""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")

        def value(name):
            try:
                return winreg.QueryValueEx(k, name)[0]
            except OSError:
                return None
        build, ubr = value("CurrentBuild"), value("UBR")
        return {"build": int(build) if build else None, "ubr": int(ubr) if ubr is not None else None,
                "edition": value("EditionID") or ""}
    except Exception:
        return {"build": None, "ubr": None, "edition": ""}


def answer_compare(text, system, data=None, today=None):
    """Ответ на «сравни …». Без двух версий — подсказка или отчёт о текущей сборке."""
    data = data or load()
    if is_windows10(text):
        return ("Я сравниваю только Windows 11. Назови две версии или сборки Windows 11, "
                "например «сравни 25H2 и 26H2».")
    tokens = find_tokens(text)
    if len(tokens) >= 2:
        return compare(tokens[0], tokens[1], data, edition_group(system.get("edition")), today)
    if not tokens and re.search(r"моя|мою|текущ|прошл|предыдущ", text, re.IGNORECASE):
        return current(system, data, today)
    if len(tokens) == 1:
        return f"Что сравнить с {tokens[0]}? Например: «сравни {tokens[0]} и 26H2»."
    return ("Назови две версии или сборки Windows 11, например «сравни 25H2 и 26H2» "
            "или «сравни 26300.8697 и 26300.9457».")


def answer_current(system, data=None, today=None):
    return current(system, data or load(), today)
