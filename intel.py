"""Режим «Windows Intelligence»: Mico внизу по центру экрана, по краю экрана светится полоса,
ответ появляется строкой над ним, а чат открывается той же комбинацией.
Здесь только расчёты без Qt — проверяются в tests/test_intel.py. Окна рисуются в intel_ui.py."""
import math
import re
import time

import sleepmode

CLASSIC = "classic"                      # Mico в углу, как раньше
INTELLIGENCE = "intelligence"            # внизу по центру, с подсветкой экрана
SUBTITLE_MAX = 200                       # сколько знаков ответа показываем в строке над Mico
LONG_ANSWER = 200                        # длиннее — строку не показываем, а плавно открываем чат
DEFAULT_ACCENT = (255, 207, 163)         # тёплый персиковый, как у Mico по умолчанию


def style_of(value):
    """Неизвестное значение из файла настроек — обычный режим."""
    return INTELLIGENCE if value == INTELLIGENCE else CLASSIC


def placement_for(style, placement):
    """В режиме Intelligence Mico всегда внизу по центру; иначе — выбранное в настройках положение."""
    return sleepmode.SPOT if style_of(style) == INTELLIGENCE else placement


def _rgb(hex_color):
    s = str(hex_color or "").lstrip("#")
    if len(s) != 6:
        return DEFAULT_ACCENT
    try:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return DEFAULT_ACCENT


def glow_colors(accent, phase, stops=4):
    """Цвета полосы по краю: от цвета Mico к светлому оттенку и обратно. Меняются плавно по phase."""
    base = _rgb(accent)
    out = []
    for i in range(stops):
        t = (math.sin(phase + i * 1.3) + 1) / 2                        # 0..1
        out.append(tuple(int(round(c + (255 - c) * 0.45 * t)) for c in base))
    return out


def approach(level, target, k=0.12):
    """Плавно тянет уровень яркости к цели и «защёлкивает» в конце, чтобы не дрожать."""
    v = level + (target - level) * k
    return target if abs(target - v) < 0.01 else v


def subtitle_text(text, limit=SUBTITLE_MAX):
    s = " ".join(str(text or "").split())
    return s if len(s) <= limit else s[:limit - 1].rstrip() + "…"


def opens_chat(text):
    """Длинный ответ — не строкой над Mico, а открываем чат, чтобы можно было прочитать."""
    return len(" ".join(str(text or "").split())) > LONG_ANSWER


# ----- функции только для Mico WI -----
SCREEN_KEY = "ctrl+alt+s"                # «Что на экране?» — скриншот и ответ моделью для экрана
WINDOW_KEY = "ctrl+alt+h"                # «Помочь с окном» — подсказка по программе, которой ты сейчас пользуешься
SCREEN_QUESTION = "сделай скриншот и коротко скажи, что сейчас на экране и что в этом важно"
GENERIC_WINDOW_QUESTION = "подскажи коротко, что полезного можно сделать в программе, которой я сейчас пользуюсь"
TODAY_QUESTION = "итог дня"              # что было за сегодня — уже есть в Mico, в WI одной кнопкой
RETRY_LABEL, TODAY_LABEL, CHAT_LABEL = "Повторить", "Итог дня", "Чат"
GATE_TEXT = ("Это функция Mico WI. Включи режим: ⚙ Настройки → Вид → Режим → «Mico · WI (BETA)». "
             "Обычный Mico эти функции не делает.")


def window_question(title):
    """Вопрос про программу, которой пользуешься. Пустое название — общий вопрос."""
    t = " ".join(str(title or "").split())[:80]
    if not t:
        return GENERIC_WINDOW_QUESTION[0].upper() + GENERIC_WINDOW_QUESTION[1:] + "."
    return f"Я сейчас в программе «{t}». Коротко подскажи, что полезного можно сделать здесь."


MIN_RAM_GB = 16                          # минимум оперативной памяти для WI
MIN_DISK_GB = 20                         # свободное место под модели и кэш
RAM_TOLERANCE_GB = 0.5                   # Windows показывает память чуть меньше номинала: 16 ГБ → 15.7 ГБ


def _has_model(name, installed):
    base = str(name or "").split(":")[0]
    return bool(base) and any(str(m).split(":")[0] == base for m in installed)


def checkup(cfg, installed, ram_gb, free_gb):
    """Проверка при включении WI: место на диске, объём памяти и обе модели.
    Возвращает список (ок или None — не удалось проверить, текст). Ничего не блокирует, только сообщает."""
    out = []
    if ram_gb is None:
        out.append((None, "Оперативную память не удалось проверить."))
    elif ram_gb + RAM_TOLERANCE_GB >= MIN_RAM_GB:
        out.append((True, f"Оперативной памяти достаточно: {ram_gb:.0f} ГБ (нужно от {MIN_RAM_GB})."))
    else:
        out.append((False, f"Оперативной памяти {ram_gb:.1f} ГБ, а нужно минимум {MIN_RAM_GB}. "
                           "WI будет работать медленно и может тормозить."))
    if free_gb is None:
        out.append((None, "Свободное место на диске не удалось проверить."))
    elif free_gb >= MIN_DISK_GB:
        out.append((True, f"Свободного места на диске {free_gb:.0f} ГБ (нужно около {MIN_DISK_GB})."))
    else:
        out.append((False, f"Свободного места на диске {free_gb:.0f} ГБ, а нужно около {MIN_DISK_GB}. "
                           "Освободи место: «что занимает место»."))
    if not installed:
        out.append((None, "Модели не проверить: Ollama не отвечает. Запусти Ollama и повтори включение WI."))
    else:
        for label, name in (("Модель для общения", cfg.get("text_model")),
                            ("Модель для экрана", cfg.get("vision_model"))):
            if _has_model(name, installed):
                out.append((True, f"{label} скачана: {name}."))
            else:
                out.append((False, f"{label} не скачана: {name}. Скачай её в ⚙ Настройки → Модели."))
    if not int(cfg.get("sleep_after_min", sleepmode.DEFAULT_MINUTES) or 0):
        out.append((False, "Mico не засыпает: он будет всё время на экране. Задай время сна в ⚙ Настройки → Поведение."))
    out.append((None, "В режиме WI я сам смотрю на экран и предупреждаю о проблемах. Это заметно нагружает компьютер, "
                      "поэтому частоту задают в ⚙ Настройки → Функции."))
    return out


def checkup_lines(cfg, installed, ram_gb, free_gb):
    """То же, что checkup, но готовым текстом с метками: ✅ ⚠️ ℹ️."""
    mark = {True: "✅", False: "⚠️", None: "ℹ️"}
    return [f"{mark[ok]} {text}" for ok, text in checkup(cfg, installed, ram_gb, free_gb)]


def subtitle_seconds(text):
    """Сколько держим строку: короткую — 4 секунды, длинную — до 12, чтобы успели прочитать."""
    return min(12.0, 4.0 + len(subtitle_text(text)) / 20)

# ----- Mico WI: состояния полоски, тишина, системные проверки, приветствие, быстрые действия -----
SESSION_SEC = 30 * 60                    # WI помнит тему разговора дольше обычного: 30 минут
STATE_NAMES = {                          # названия действий для полоски (как видит пользователь)
    "listen": "Слушает", "think": "Думает", "break": "Перерыв",
    "watch": "Наблюдение", "tip": "Подсказка", "warn": "Предупреждение",
}
DEFAULT_COLORS = {                       # по умолчанию у каждого действия свой цвет — иначе их не различить
    "listen": "#FFCFA3",                 # слушает — тёплый цвет Mico
    "think": "#FFA94D",                  # думает над ответом — ярче и теплее
    "break": "#9BE3A8",                  # пора отдохнуть — зелёный
    "watch": "#D6B8FF",                  # посмотрел на экран и хочет что-то сказать — сиреневый
    "tip": "#9FD3FF",                    # подсказка, приветствие, итог — голубой
    "warn": "#FF9F9F",                   # что-то мешает работе — красноватый
}
STATE_COLORS = DEFAULT_COLORS            # прежнее имя, остаётся для совместимости
_HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def state_colors(cfg):
    """Цвета полоски из настроек. Неверные значения и повторы заменяются стандартными,
    чтобы у двух действий никогда не оказался один и тот же цвет."""
    raw = cfg.get("wi_colors") if isinstance(cfg.get("wi_colors"), dict) else {}
    out = {}
    for key, default in DEFAULT_COLORS.items():
        v = raw.get(key)
        out[key] = v.upper() if isinstance(v, str) and _HEX.fullmatch(v) else default
    if len(set(out.values())) != len(out):
        return dict(DEFAULT_COLORS)
    return out


def state_color(cfg, state):
    return state_colors(cfg).get(state, DEFAULT_COLORS.get(state, DEFAULT_COLORS["listen"]))


def color_clash(colors, state, hex_color):
    """Какое действие уже использует этот цвет (кроме state). None — цвет свободен."""
    h = str(hex_color).upper()
    for key, value in colors.items():
        if key != state and value.upper() == h:
            return key
    return None


QUICK_ACTIONS = [                        # кнопка «⚡» под ответом: фразы, которые Mico уже умеет выполнять
    ("Тёмная тема", "включи тёмную тему"),
    ("Светлая тема", "включи светлую тему"),
    ("Не беспокоить", "включи не беспокоить"),
    ("Выключить звук", "выключи звук"),
    ("Скриншот", "сделай скриншот"),
    ("Который час", "который час"),
]
WARN_GAP_SEC = 2 * 3600                  # одну и ту же проблему напоминаем не чаще раза в два часа
DISK_LOW_GB = 10
MEM_HIGH_PCT = 90
BATTERY_LOW_PCT = 15


def is_fullscreen(win, mon, tol=2):
    """Окно занимает весь монитор (с допуском в пиксели). Прямоугольники — (left, top, right, bottom)."""
    if not win or not mon:
        return False
    return all(abs(a - b) <= tol for a, b in zip(win, mon))


def problems(disk_free_gb=None, mem_pct=None, battery_pct=None, plugged=True):
    """Что мешает работе сейчас: список (ключ, текст). Неизвестные значения (None) пропускаем."""
    out = []
    if disk_free_gb is not None and disk_free_gb < DISK_LOW_GB:
        out.append(("disk", f"Мало места на диске: осталось {disk_free_gb:.1f} ГБ. "
                            "Спроси «что занимает место» — покажу, что можно почистить."))
    if mem_pct is not None and mem_pct >= MEM_HIGH_PCT:
        out.append(("mem", f"Оперативная память почти заполнена ({int(mem_pct)}%). "
                           "Закрой лишние программы или вкладки браузера."))
    if battery_pct is not None and battery_pct < BATTERY_LOW_PCT and not plugged:
        out.append(("battery", f"Батарея садится ({int(battery_pct)}%). Подключи зарядку или включи экономию."))
    return out


def warn_due(key, now, last):
    """Можно ли снова напомнить о проблеме: прошло больше WARN_GAP_SEC с прошлого раза."""
    return now - last.get(key, -WARN_GAP_SEC * 2) >= WARN_GAP_SEC


def greeting_line(hello_text, summary_text, limit=SUBTITLE_MAX):
    """Приветствие в WI — строка над Mico: первая фраза приветствия и первая строка итога дня."""
    first = " ".join(str(hello_text or "").split())
    first = first.split(". ")[0].split("! ")[0].strip()
    summary = " ".join(str(summary_text or "").split())
    line = first + (" Итог: " + summary if summary else "")
    return subtitle_text(line, limit)


# ----- Mico WI: толщина полоски, волны при ответе, переход, тур, моргание (чистая логика) -----
THICK_MIN, THICK_MAX, THICK_DEFAULT = 2, 24, 4     # толщина полоски, px: тоньше — не видно, толще — мешает
WAVE_SOURCES = {                                    # откуда цвет волн: из персонализации Mico, цвета действия, свой или набор
    "mico": "Цвет Mico (из персонализации)",
    "state": "Цвет действия",
    "custom": "Свой цвет",
    "theme": "Готовый набор",
}
# Готовые наборы волн: несколько цветов, которые плавно сменяют друг друга, пока волна бежит.
WAVE_THEMES = {
    "auto": ("Само по времени суток", None),
    "sunset": ("Закат", ["#FF9F6B", "#FFCFA3", "#FF7EB6"]),
    "ocean": ("Океан", ["#7FB8FF", "#9FD3FF", "#5EE0D0"]),
    "mint": ("Мята", ["#9BE3A8", "#7FE0C0", "#C6F6A8"]),
    "lavender": ("Лаванда", ["#D6B8FF", "#B9A0FF", "#FFB8E6"]),
}
WAVE_THEME_DEFAULT = "auto"

WAVE_DEFAULT_CUSTOM = "#FFCFA3"
TOUR = [                                            # что Mico рассказывает сразу после включения WI, по одной строке
    "Я теперь внизу по центру экрана — там, где меня видно и где я никому не мешаю.",
    "Полоска по краю показывает, чем я занят: слушаю, думаю, напоминаю о перерыве. Цвет каждого действия можно выбрать.",
    "Когда я отвечаю, полоска слегка волнуется — так видно, что я работаю.",
    "Ctrl+Alt+S — «что на экране?»: я посмотрю на экран и коротко скажу главное. "
    "Ctrl+Alt+H — помогу с программой, которой ты пользуешься сейчас.",
    "Короткий ответ появится строкой надо мной. Длинный сам откроет этот чат, чтобы его было удобно читать.",
    "Если ты меня долго не трогаешь, я плавно уплываю вниз и растворяюсь. Вернуть меня можно вопросом или горячей клавишей.",
]
TOUR_GAP_MS = 1500                                   # пауза между строками тура: как будто печатаю
EDGE_SWEEP_SEC = 0.8                                 # свечение и капсула появляются плавно
STATE_TEXT = {                                       # короткая строка рядом с Mico: что он делает сейчас
    "listen": "слушаю", "think": "думаю…", "break": "пора отдохнуть",
    "watch": "вижу", "tip": "совет", "warn": "внимание",
}


def glow_height(cfg):
    """Высота свечения внизу экрана, px: тонкое — 48, толстое — до 180. По умолчанию — около 88."""
    return 48 + thickness(cfg) * 10                                        # небольшое скругление углов полоски по краям экрана, px
ARRIVE_SEC = 0.42                                    # Mico выезжает из угла в центр внизу
LEAVE_SEC = 0.35                                     # и уезжает обратно, когда WI выключили
SLEEP_DROP_PX = 90                                   # во сне Mico уходит вниз на столько пикселей
BLINK_SEC = 0.2                                      # одно моргание: закрылся и открылся
_RGB_HEX = re.compile(r"#([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})")


def thickness(cfg):
    """Толщина полоски из настроек, в допустимых пределах. Мусор — стандартная."""
    try:
        v = int(round(float(cfg.get("wi_thickness", THICK_DEFAULT))))
    except (TypeError, ValueError):
        v = THICK_DEFAULT
    return max(THICK_MIN, min(THICK_MAX, v))


def waves_on(cfg):
    return bool(cfg.get("wi_waves", True))


GLOW_WAVES = "waves"                       # волны внизу экрана (как раньше)
GLOW_EDGES = "edges"                       # нежные полоски вдоль низа, боков и верха, как у Apple Intelligence
GLOW_STYLES = (GLOW_WAVES, GLOW_EDGES)
GLOW_DEFAULT = GLOW_WAVES


def glow_style(cfg):
    """Какой вид подсветки выбран: волны или полоски по краям. Неизвестное значение — волны."""
    value = str(cfg.get("wi_glow_style", GLOW_DEFAULT))
    return value if value in GLOW_STYLES else GLOW_DEFAULT


WAVE_HEIGHT_MIN, WAVE_HEIGHT_MAX, WAVE_HEIGHT_DEFAULT = 30, 200, 100   # толщина волн, % от стандартной


def wave_height(cfg):
    """Толщина (высота) волн в процентах от стандартной: 100 — как было. Мусор — стандартная."""
    try:
        v = int(round(float(cfg.get("wi_wave_height", WAVE_HEIGHT_DEFAULT))))
    except (TypeError, ValueError):
        v = WAVE_HEIGHT_DEFAULT
    return max(WAVE_HEIGHT_MIN, min(WAVE_HEIGHT_MAX, v))


def glow_visible(cfg):
    """Подсветка видна постоянно: в виде волн или полосок. Без неё режим WI работает, но экран не подсвечен."""
    return glow_style(cfg) == GLOW_EDGES or waves_on(cfg)


EDGE_W_MIN, EDGE_W_MAX, EDGE_W_DEFAULT = 6, 120, 30    # толщина полосок по краям, px


def edge_band(cfg):
    """Ширина полосок у края экрана, px — своя настройка «Толщина полосок по краям»."""
    try:
        v = int(round(float(cfg.get("wi_edge_width", EDGE_W_DEFAULT))))
    except (TypeError, ValueError):
        v = EDGE_W_DEFAULT
    return max(EDGE_W_MIN, min(EDGE_W_MAX, v))


def edge_alpha(cfg):
    """Прозрачность полосок — та же, что у волн («Прозрачность волн и полосок»). 85 — как по умолчанию."""
    try:
        v = float(cfg.get("wave_opacity", 85))
    except (TypeError, ValueError):
        v = 85.0
    return max(0.0, min(100.0, v)) / 100.0 * 1.2       # 1.2: при 100 полоски чуть заметнее, при 0 — не видны


def wave_color(cfg, state):
    """Цвет волн: по выбору пользователя — цвет Mico из персонализации, цвет действия или свой."""
    src = cfg.get("wi_wave_source", "mico")
    if src == "custom" and _HEX.fullmatch(str(cfg.get("wi_wave_custom", ""))):
        return str(cfg["wi_wave_custom"]).upper()
    if src == "mico" and _HEX.fullmatch(str(cfg.get("color", ""))):
        return str(cfg["color"]).upper()
    if src == "theme":
        return theme_colors(cfg)[0].upper()
    return state_color(cfg, state)


def plain_from_html(h):
    """Ответ в виде карточек или списка — в обычный текст для чата WI. Пустой результат — короткая подсказка."""
    t = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</tr>|</div>|</h\d>", "\n", str(h or ""))
    t = re.sub(r"<[^>]+>", "", t)
    import html as _html
    t = _html.unescape(t)
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    out = "\n".join(lines)[:1500]
    return out or "Ответ оформлен карточками — полностью он виден в обычном окне Mico."


def theme_for_hour(hour):
    """Для режима «по времени суток»: утро — мята, день — океан, вечер — закат, ночь — лаванда."""
    if 5 <= hour < 11:
        return "mint"
    if 11 <= hour < 17:
        return "ocean"
    if 17 <= hour < 22:
        return "sunset"
    return "lavender"


def theme_colors(cfg, hour=None):
    """Список цветов выбранного набора. Неизвестный набор — «по времени суток»."""
    key = str(cfg.get("wi_wave_theme", WAVE_THEME_DEFAULT))
    if key not in WAVE_THEMES or key == "auto":
        if hour is None:
            hour = time.localtime().tm_hour
        key = theme_for_hour(hour)
    return list(WAVE_THEMES[key][1])


def wave_base(cfg, state, phase=0.0, hour=None):
    """Базовый цвет волны в этот момент. Для набора — плавный переход между его цветами по phase."""
    if cfg.get("wi_wave_source") != "theme":
        return wave_color(cfg, state)
    cols = [_rgb(c) for c in theme_colors(cfg, hour)]
    n = len(cols)
    pos = (phase / (2 * math.pi)) % n                      # сколько цветов уже прошли
    i = int(pos) % n
    return "#%02X%02X%02X" % lerp_rgb(cols[i], cols[(i + 1) % n], pos - int(pos))


def hex_rgb(hex_color):
    """#RRGGBB → (r, g, b). Неверный цвет — персиковый, как у Mico."""
    m = _RGB_HEX.fullmatch(str(hex_color or ""))
    if not m:
        return DEFAULT_ACCENT
    return tuple(int(x, 16) for x in m.groups())


def lerp_rgb(a, b, k):
    """Плавный переход между двумя цветами: k от 0 до 1."""
    k = max(0.0, min(1.0, k))
    return tuple(int(round(x + (y - x) * k)) for x, y in zip(a, b))


def ease_io(p):
    """Плавный старт и плавный финиш: 0..1 → 0..1 (smoothstep)."""
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def sweep_lengths(w, h, p):
    """Полоска расходится от середины низа: по обе стороны — вдоль низа к углам, вверх по боку,
    потом над верхом к центру. p от 0 до 1. Возвращает освещённую длину на одной стороне:
    (низ, бок, верх). Сумма путей по обе стороны от середины низа до середины верха — w + h."""
    half = w / 2
    d = max(0.0, min(1.0, p)) * (w + h)
    return (min(d, half), min(max(d - half, 0.0), h), min(max(d - half - h, 0.0), half))


def pulse(x, a, b):
    """Гладкий «колокол» от 0 до 1 на отрезке [a, b] и 0 вне его."""
    if x <= a or x >= b:
        return 0.0
    return math.sin(math.pi * (x - a) / (b - a))


def blink_close(u):
    """Насколько закрыт глаз при одном моргании: u от 0 до 1 — доля моргания. 0 — открыт, 1 — закрыт."""
    return pulse(u, 0.0, 1.0)


def double_blink_close(u):
    """Двойное моргание из анимации «blink2»: два плавных прикрытия, без резких переходов."""
    return max(pulse(u, 0.0, 0.3), pulse(u, 0.4, 0.7))


def speak_seconds(text):
    """Сколько Mico «говорит» ответ: как долго идёт тот самый разговор и волны на полоске."""
    return max(1.5, min(12.0, 0.028 * len(" ".join(str(text or "").split()))))


def tour_lines(checkup_lines=()):
    """Тур по WI: фразы по порядку. Если есть проверка при включении — она последней строкой."""
    lines = list(TOUR)
    if checkup_lines:
        lines.append("Проверка при включении:\n" + "\n".join(checkup_lines))
    return lines


# ----- Mico WI: помощник по буферу, реакция на ошибки, файлы, таймлайн (тексты запросов и подписи) -----
EXPLAIN_PROMPT = ("Это текст ошибки с компьютера пользователя. Объясни простыми словами, что случилось, "
                  "и предложи 2–3 понятных шага. Не выдумывай причину, если её нет в тексте. Отвечай кратко.\n\nТекст:\n")
HUNG_PROMPT = ("Программа «{proc}» перестала отвечать. Дай 3 коротких безопасных шага: подождать, сохранить работу, "
               "что проверить. Не предлагай терять данные и не предлагай завершать программу без предупреждения.")
FILE_PROMPT = ("Коротко перескажи файл «{name}»: о чём он, главное и что в нём важно. Не выдумывай то, чего нет "
               "в тексте. Отвечай 3–5 предложениями.\n\nТекст файла:\n{text}")
IMAGE_PROMPT = "Коротко опиши, что на картинке и что в ней важно. Отвечай 2–4 предложениями."
FILE_UNSUPPORTED = "Пока я умею читать текстовые файлы и картинки. Этот тип файла я пока не понимаю."
CLIP_OFFER_GAP_SEC = 60          # о тексте ошибки в буфере не напоминаем чаще раза в минуту
ERROR_CHECK_MS = 2000            # как часто смотрим на окно на переднем плане


def explain_prompt(text):
    return EXPLAIN_PROMPT + str(text or "")[:1500]


def file_prompt(name, text):
    return FILE_PROMPT.format(name=name, text=str(text or "")[:6000])


def hung_prompt(proc):
    return HUNG_PROMPT.format(proc=proc or "программа")


# ----- Mico WI: тихий час, «не беспокоить», короче/подробнее, чат с файлом, загрузка -----
DND_CHOICES = [(30, "На 30 минут"), (60, "На час"), (120, "На два часа"), (0, "Выключить")]
FILE_TTL_SEC = 30 * 60                     # файл помним в чате WI полчаса без новых вопросов
REWRITE_LABELS = {"short": "Короче", "long": "Подробнее"}
REWRITE_PROMPTS = {
    "short": "Перепиши этот ответ короче: 1–2 предложения, только главное, без вступлений.\n\n",
    "long": "Раскрой этот ответ подробнее: добавь объяснение и 2–3 понятных шага. Ничего не выдумывай.\n\n",
}
FILE_CHAT_PROMPT = ("Отвечай на вопрос, опираясь только на файл «{name}». Если в файле ответа нет, так и скажи.\n\n"
                    "Файл:\n{text}\n\nВопрос: {question}")
IMAGE_CHAT_PROMPT = "Ответь на вопрос про картинку. Если по картинке ответа не видно, так и скажи.\n\nВопрос: {question}"


def minutes_of(hhmm):
    """«HH:MM» → минуты от полуночи. Неверное значение — None."""
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(hhmm or ""))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return h * 60 + mi if h < 24 and mi < 60 else None


def in_quiet_hours(now, start, end, on=True):
    """Тихий час: с start до end по местному времени. Через полночь тоже работает (23:00–08:00).
    start == end или неверное время — тихого часа нет."""
    if not on:
        return False
    s, e = minutes_of(start), minutes_of(end)
    if s is None or e is None or s == e:
        return False
    t = time.localtime(now)
    cur = t.tm_hour * 60 + t.tm_min
    return s <= cur < e if s < e else (cur >= s or cur < e)


def load_percent(value):
    """Загрузка процессора в процентах, 0–100. Не число — 0."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, v))


# ----- волны внизу экрана: только расчёт, рисуется в intel_ui.py -----
WAVE_LAYERS = ((1.0, 0.9, 0.0), (1.7, -0.6, 1.3), (2.6, 0.45, 2.1))   # (частота по ширине, скорость, фаза)
WAVE_BUMPS = (0.18, 0.46, 0.74)                                         # места, где волна поднимается при ответе


def wave_profile(n, t, answer=0.0, bumps=WAVE_BUMPS, breathe=True):
    """Высоты гребней волны от 0 до 1 по n колонкам слева направо.
    t — время (плавно растёт), answer — 0..1: насколько волна поднимается при ответе (в нескольких местах).
    Всё непрерывно: соседние колонки отличаются мало, поэтому движение плавное."""
    n = max(2, int(n))
    breath = (0.9 + 0.1 * math.sin(t * 0.7)) if breathe else 1.0       # дыхание — едва заметно
    out = []
    for i in range(n):
        x = i / (n - 1)
        base = 0.35
        for freq, speed, ph in WAVE_LAYERS:
            amp = 0.15 if freq == WAVE_LAYERS[0][0] else (0.1 if freq == WAVE_LAYERS[1][0] else 0.05)
            base += amp * math.sin(2 * math.pi * freq * x + speed * t + ph)
        bump = 0.0
        if answer > 0.0:
            for c in bumps:
                cc = c + 0.06 * math.sin(t * 0.5 + c * 6)              # гребни чуть ходят туда-сюда
                bump += 0.9 * math.exp(-((x - cc) / 0.1) ** 2)
        h = (base * breath) / 0.65 + answer * min(1.0, bump) * 0.45
        out.append(max(0.0, min(1.0, h)))
    return out
