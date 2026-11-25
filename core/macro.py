"""Макросы («цепочки»): «запомни цепочку утро: погода; открой почту; включи плейлист» —
и одной командой «макрос утро» всё выполняется по очереди. Хранятся в настройках пользователя.
Чистая логика — проверяется в tests/test_agent_extras.py без Windows и без модели."""
import re

# «запомни цепочку утро: погода; открой почту; включи плейлист» — и вариации слов
SAVE = re.compile(r"^(?:запомни|сохрани|создай)\s+(?:цепочк\w*|макрос|сценарий)\s+(?P<name>[^:;]{2,30}?)\s*[:,]\s*(?P<steps>.+)$",
                  re.IGNORECASE)
# «макрос утро», «выполни цепочку утро», «запусти макрос утро»
RUN = re.compile(r"^(?:(?:выполни|запусти|прогони)\s+(?:макрос|цепочк\w*|сценарий)\s+|"
                 r"(?:макрос|цепочк\w*)\s+)(?P<name>.+?)\s*[!.]?$", re.IGNORECASE)

MAX_STEPS = 8                   # длинные цепочки — уже не макрос, а сценарий для агента
MIN_STEPS = 2                   # одна команда — это не цепочка, она и так запоминается


def _norm(s):
    return " ".join(str(s or "").lower().replace("ё", "е").split())


def parse_save(q):
    """«запомни цепочку утро: …» → {'name': 'утро', 'steps': [...]} или None."""
    m = SAVE.match(_norm(q).strip(" .!?")) or SAVE.match(" ".join(str(q or "").split()))
    if not m:
        return None
    steps = [s.strip() for s in re.split(r";|\bпотом\b|\bзатем\b", m.group("steps")) if s.strip()]
    if not (MIN_STEPS <= len(steps) <= MAX_STEPS):
        return None
    name = m.group("name").strip()
    return {"name": name, "steps": steps} if name else None


def parse_run(q):
    """«макрос утро» → 'утро' или None. Существование проверяется отдельно в get()."""
    m = RUN.match(_norm(q).strip(" .!?"))
    return m.group("name").strip() if m else None


def add(cfg, name, steps):
    """Сохраняет цепочку в настройках. Возвращает сохранённые шаги."""
    macros = dict(cfg.get("macros") or {})
    macros[_norm(name)] = list(steps)[:MAX_STEPS]
    cfg["macros"] = macros
    return macros[_norm(name)]


def get(cfg, name):
    """Шаги цепочки или None, если такой нет. Ищем без учёта регистра и «ё»."""
    return (cfg.get("macros") or {}).get(_norm(name))


def names(cfg):
    return sorted(cfg.get("macros") or {})


def describe(name, steps):
    """Человеку: что запомнили и как запустить."""
    lines = [f"Запомнил цепочку «{name}» ({len(steps)} шага):"]
    for i, s in enumerate(steps, 1):
        lines.append(f"{i}. {s}")
    lines.append(f"Запусти: «макрос {name}».")
    return "\n".join(lines)
