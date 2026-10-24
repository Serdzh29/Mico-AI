"""Кнопки под чатом. Каталог — всё, что умеет Mico. Режимы:
  auto   — Mico AI подбирает кнопки сам: чаще нажимаемые встречаются чаще, но набор и порядок меняются;
  manual — пользователь выбирает до 6 кнопок в ⚙ Настройки → Кнопки.
Учёт нажатий — только по тому, что пользователь просит у Mico AI (не по другим программам)."""
import math, random, re
from dataclasses import dataclass

import components

MAX_CHIPS = 6


@dataclass
class Chip:
    id: str
    label: str
    phrase: str
    send: bool            # True — отправить сразу; False — вставить в строку ввода (дописать своё)
    match: str            # регулярное выражение: по нему понимаем, что пользователь нажал/написал эту команду


BASE = [
    Chip("screenshot", "Скриншот", "сделай скриншот", True, r"скриншот|скрин\b"),
    Chip("screen", "Что на экране?", "что у меня на экране?", True, r"на экране|что я вижу"),
    Chip("recap", "Что я делал?", "что я делал час назад?", True, r"что я делал"),
    Chip("open", "Открыть…", "открой ", False, r"^(открой|запусти)\b"),
    Chip("site", "Открыть сайт", "открой сайт ", False, r"открой сайт"),
    Chip("settings", "Настройки Windows", "открой настройки ", False, r"настройк"),
    Chip("can", "Что умеешь?", "что ты умеешь?", True, r"что ты умеешь"),
    Chip("reply", "Помочь ответить", "помоги ответить другу", True, r"помоги ответить|ответ.*друг"),
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


def reset(cfg):
    cfg["chip_usage"] = {}
