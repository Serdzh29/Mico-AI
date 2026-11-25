"""Кнопки под чатом. Каталог — всё, что умеет Mico. Режимы:
  auto   — Mico AI подбирает кнопки сам: чаще нажимаемые встречаются чаще, но набор и порядок меняются;
  manual — пользователь выбирает до 6 кнопок в ⚙ Настройки → Кнопки.
Учёт нажатий — только по тому, что пользователь просит у Mico AI (не по другим программам)."""
import math, random, re, time
from dataclasses import dataclass, replace

from core import habits
from ui import widgets as components

MAX_CHIPS = 6


@dataclass
class Chip:
    id: str
    label: str
    phrase: str
    send: bool            # True — отправить сразу; False — вставить в строку ввода (дописать своё)
    match: str            # регулярное выражение: по нему понимаем, что пользователь нажал/написал эту команду
    personal: bool = False  # предложена по привычкам человека, а не из стандартного набора


BASE = [
    Chip("screenshot", "Скриншот", "сделай скриншот", True, r"скриншот|скрин\b"),
    Chip("recap", "Что я делал?", "что я делал час назад?", True, r"что я делал"),
    Chip("open", "Открыть…", "открой ", False, r"^(открой|запусти)\b"),
    Chip("site", "Открыть сайт", "открой сайт ", False, r"открой сайт"),
    Chip("settings", "Настройки Windows", "открой настройки ", False, r"настройк"),
    Chip("can", "Что умеешь?", "что ты умеешь?", True, r"что ты умеешь"),
    Chip("timer", "Таймер 10 мин", "поставь таймер на 10 минут", True, r"таймер"),
    Chip("remind", "Напомнить", "напомни через час ", False, r"напомни"),
    Chip("alarm", "Будильник", "поставь будильник на ", False, r"будильник"),
    Chip("vol_up", "Громче", "громче", True, r"громче|прибавь громкость"),
    Chip("vol_down", "Тише", "тише", True, r"тише|убавь громкость"),
    Chip("mute", "Без звука", "выключи звук", True, r"выключи звук|без звука"),
    Chip("bright_up", "Ярче", "ярче", True, r"ярче"),
    Chip("bright_down", "Темнее", "темнее", True, r"темнее"),
    Chip("next", "Следующий трек", "переключи трек", True, r"трек|песн"),
    Chip("prev", "Предыдущий трек", "предыдущий трек", True, r"предыдущ\w* трек"),
    Chip("pause", "Пауза", "пауза", True, r"пауза"),
    Chip("lock", "Заблокировать", "заблокируй пк", True, r"заблокируй"),
    Chip("sleep", "Спящий режим", "спящий режим", True, r"спящий режим"),
    Chip("minimize", "Свернуть всё", "сверни все окна", True, r"сверни все"),
    Chip("desktop", "Новый рабочий стол", "новый рабочий стол", True, r"рабочий стол"),
    Chip("dark", "Тёмная тема", "включи тёмную тему", True, r"тёмн\w* тем|темн\w* тем"),
    Chip("light", "Светлая тема", "включи светлую тему", True, r"светл\w* тем"),
    Chip("battery", "Заряд батареи", "заряд батареи", True, r"заряд"),
    Chip("cpu", "Что грузит ПК", "что грузит процессор", True, r"грузит"),
    Chip("disk", "Место на диске", "сколько места на диске", True, r"места на диске"),
    Chip("updates", "Обновления", "проверь обновления", True, r"обновлени"),
    Chip("dns", "Очистить DNS", "очисти кэш dns", True, r"dns"),
    Chip("tasks", "Диспетчер задач", "открой диспетчер задач", True, r"диспетчер задач"),
]


def _toggle_chips():
    out = []
    for i, t in enumerate(components.TOGGLES):
        if not t.keys:
            continue
        key = t.keys[0]
        pattern = "|".join(re.escape(k) for k in sorted(t.keys, key=len, reverse=True))
        # переключателей больше, чем эмодзи: лишним даём общий значок, а не падаем с IndexError
        out.append(Chip(f"t:{i}", t.name, f"включи {key}", True, pattern))
    return out


CATALOG = BASE + _toggle_chips()
BY_ID = {c.id: c for c in CATALOG}
_MATCH = [(c, re.compile(c.match, re.IGNORECASE)) for c in CATALOG]


def record(text, cfg):
    """Запоминает, какой кнопкой (командой) пользуется человек. Меняет cfg['chip_usage']."""
    low = (text or "").lower().replace("ё", "е")
    for c, rx in _MATCH:
        if rx.search(low):
            usage = cfg.setdefault("chip_usage", {})
            usage[c.id] = usage.get(c.id, 0) + 1
            habits.note_command(cfg, c.id)          # и в какое время дня её просят
            return c.id
    return None


def _weight(usage):
    # логарифм, чтобы частая кнопка доминировала, но не занимала всё место
    return 1.0 + 2.0 * math.log1p(usage)


def pick(cfg, rng=random):
    """Какие кнопки показать сейчас (список Chip)."""
    count = max(0, min(MAX_CHIPS, int(cfg.get("chips_count", MAX_CHIPS))))
    if count == 0:                            # 0 — кнопки полностью убраны (настройка «не показывать»)
        return []
    if cfg.get("chips_mode", "auto") == "manual":
        pinned = [BY_ID[i] for i in cfg.get("chips_pinned", []) if i in BY_ID]
        if pinned:
            return pinned[:MAX_CHIPS]          # пустой ручной набор — временно показываем авто-набор
    usage = cfg.get("chip_usage", {})
    pool = sorted(CATALOG, key=lambda c: -usage.get(c.id, 0))[:18]
    weights = {c.id: _weight(usage.get(c.id, 0)) for c in pool}
    chosen, left = [], list(pool)
    while left and len(chosen) < count:
        total = sum(weights[c.id] for c in left)
        r, acc = rng.uniform(0, total), 0.0
        for c in left:
            acc += weights[c.id]
            if acc >= r:
                chosen.append(c)
                left.remove(c)
                break
    rng.shuffle(chosen)                  # порядок тоже меняется
    return chosen


WELCOME_COUNT = 4


DAYTIME = {                                  # что обычно нужно в это время дня (пока своих привычек мало)
    "morning": ["recap", "updates", "bright_up", "timer", "cpu", "screenshot"],
    "day": ["screenshot", "timer", "cpu", "minimize", "recap", "disk"],
    "evening": ["dark", "bright_down", "recap", "pause", "timer", "screenshot"],
    "night": ["dark", "bright_down", "sleep", "lock", "mute", "recap"],
}


def _by_daytime(now):
    """Стандартные кнопки по времени суток. Порядок слегка меняется каждый час, чтобы набор не был застывшим."""
    lt = time.localtime(now)
    h = lt.tm_hour
    part = "morning" if 6 <= h < 11 else "day" if h < 18 and h >= 11 else "evening" if 18 <= h < 23 else "night"
    ids = list(DAYTIME[part])
    head, tail = ids[:2], ids[2:]
    random.Random(lt.tm_yday * 24 + h).shuffle(tail)     # первые две — самые уместные, остальные чередуются
    out = [BY_ID[i] for i in head + tail if i in BY_ID]
    return out + [c for c in BASE if c not in out]


def app_chip(process, name):
    """Быстрое действие «Открыть <программу>» для часто используемой программы."""
    return Chip(f"app:{process}", f"Открыть {name}", f"открой {name}", True,
                r"^(открой|запусти)\s+" + re.escape(name.lower()), personal=True)


def welcome(cfg, rng=random, apps=None, now=None):
    """Кнопки на пустом экране — по привычкам человека на ПК:
    команды, которые он чаще всего просит у Mico (с учётом времени дня), и программы, в которых он
    больше всего работает (apps — {process: вес} из core.habits.app_usage). Только действия, которые
    Mico выполняет сразу (send=True). Новичку (привычек ещё нет) — стандартный набор."""
    now = time.time() if now is None else now
    usage = cfg.get("chip_usage", {}) or {}
    used = sorted((c for c in CATALOG if c.send and usage.get(c.id, 0) > 0),
                  key=lambda c: (-habits.command_score(cfg, c.id, now), CATALOG.index(c)))
    used = [replace(c, personal=True) for c in used]
    app_list = [] if not cfg.get("habit_suggest", True) else [app_chip(p, n) for p, n in habits.top_apps(apps or {}, 2)]
    out = []
    while (used or app_list) and len(out) < WELCOME_COUNT:   # чередуем: частая команда, частая программа…
        if used:
            out.append(used.pop(0))
        if app_list and len(out) < WELCOME_COUNT:
            out.append(app_list.pop(0))
    for c in _by_daytime(now):                       # добираем подходящими для этого времени дня
        if len(out) >= WELCOME_COUNT:
            break
        if c.send and all(o.id != c.id for o in out):
            out.append(c)
    return out[:WELCOME_COUNT]


def reset(cfg):
    cfg["chip_usage"] = {}
