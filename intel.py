"""Режим «Windows Intelligence»: Mico AI внизу по центру экрана, по краю экрана светится полоса,
ответ появляется строкой над ним, а чат открывается той же комбинацией.
Здесь только расчёты без Qt — проверяются в tests/test_intel.py. Окна рисуются в intel_ui.py."""
import math
import re
import time


import sleepmode

CLASSIC = "classic"                      # Mico AI в углу, как раньше
INTELLIGENCE = "intelligence"            # внизу по центру, с подсветкой экрана
SUBTITLE_MAX = 200                       # сколько знаков ответа показываем в строке над Mico AI
LONG_ANSWER = 200                        # длиннее — строку не показываем, а плавно открываем чат
DEFAULT_ACCENT = (255, 207, 163)         # тёплый персиковый, как у Mico AI по умолчанию


def style_of(value):
    """Mico AI — единственный режим. Значение из старых настроек ни на что не влияет."""
    return INTELLIGENCE


def placement_for(style, placement):
    """В режиме Intelligence Mico AI всегда внизу по центру; иначе — выбранное в настройках положение."""
    return sleepmode.SPOT if style_of(style) == INTELLIGENCE else placement


def _rgb(hex_color):
    s = str(hex_color or "").lstrip("#")
    if len(s) != 6:
        return DEFAULT_ACCENT
    try:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return DEFAULT_ACCENT


def approach(level, target, k=0.12):
    """Плавно тянет уровень яркости к цели и «защёлкивает» в конце, чтобы не дрожать."""
    v = level + (target - level) * k
    return target if abs(target - v) < 0.01 else v


def subtitle_text(text, limit=SUBTITLE_MAX):
    s = " ".join(str(text or "").split())
    return s if len(s) <= limit else s[:limit - 1].rstrip() + "…"


def chat_opacity(cfg=None):
    """Прозрачности нет: чаты Mico AI всегда непрозрачные (матовое тёмное стекло)."""
    return 1.0


def opens_chat(text):
    """Длинный ответ — не строкой над Mico AI, а открываем чат, чтобы можно было прочитать."""
    return len(" ".join(str(text or "").split())) > LONG_ANSWER


# ----- функции только для Mico AI -----
SCREEN_KEY = "ctrl+alt+s"                # «Что на экране?» — скриншот и ответ моделью для экрана
WINDOW_KEY = "ctrl+alt+h"                # «Помочь с окном» — подсказка по программе, которой ты сейчас пользуешься
SCREEN_QUESTION = "сделай скриншот и коротко скажи, что сейчас на экране и что в этом важно"
GENERIC_WINDOW_QUESTION = "подскажи коротко, что полезного можно сделать в программе, которой я сейчас пользуюсь"
RETRY_LABEL, CHAT_LABEL = "Повторить", "Чат"
GATE_TEXT = "Эта функция уже работает в Mico AI."


def window_question(title):
    """Вопрос про программу, которой пользуешься. Пустое название — общий вопрос."""
    t = " ".join(str(title or "").split())[:80]
    if not t:
        return GENERIC_WINDOW_QUESTION[0].upper() + GENERIC_WINDOW_QUESTION[1:] + "."
    return f"Я сейчас в программе «{t}». Коротко подскажи, что полезного можно сделать здесь."


MIN_RAM_GB = 16                          # минимум оперативной памяти для Mico AI
MIN_DISK_GB = 20                         # свободное место под модели и кэш
RAM_TOLERANCE_GB = 0.5                   # Windows показывает память чуть меньше номинала: 16 ГБ → 15.7 ГБ


def _has_model(name, installed):
    base = str(name or "").split(":")[0]
    return bool(base) and any(str(m).split(":")[0] == base for m in installed)


def block_reasons(ram_gb, free_gb):
    """Почему Mico AI нельзя включить. Пустой список — можно.
    Жёсткое ограничение: меньше MIN_RAM_GB памяти или меньше MIN_DISK_GB свободного места.
    Если значение не удалось прочитать (None), не запрещаем: нельзя проверить — не блокируем."""
    reasons = []
    if ram_gb is not None and ram_gb + RAM_TOLERANCE_GB < MIN_RAM_GB:
        reasons.append(f"оперативной памяти {ram_gb:.1f} ГБ, а нужно минимум {MIN_RAM_GB} ГБ")
    if free_gb is not None and free_gb < MIN_DISK_GB:
        reasons.append(f"свободного места на диске {free_gb:.0f} ГБ, а нужно минимум {MIN_DISK_GB} ГБ")
    return reasons


def block_message(reasons):
    """Текст отказа для пользователя."""
    return ("Режим Mico AI не включён: " + "; ".join(reasons) + ". "
            "Mico AI работает, но на этом ПК он может тормозить. Закрой лишние программы или освободи место на диске.")


def enforce_mode(cfg, ram_gb, free_gb):
    """При запуске: если ПК слабее нужного, Mico AI работает всё равно, но предупреждаем.
    Возвращает текст для показа в чате или None."""
    reasons = block_reasons(ram_gb, free_gb)
    return block_message(reasons) if reasons else None


def checkup(cfg, installed, ram_gb, free_gb):
    """Проверка при включении Mico AI: место на диске, объём памяти и обе модели.
    Возвращает список (ок или None — не удалось проверить, текст). Ничего не блокирует, только сообщает."""
    out = []
    if ram_gb is None:
        out.append((None, "Оперативную память не удалось проверить."))
    elif ram_gb + RAM_TOLERANCE_GB >= MIN_RAM_GB:
        out.append((True, f"Оперативной памяти достаточно: {ram_gb:.0f} ГБ (нужно от {MIN_RAM_GB})."))
    else:
        out.append((False, f"Оперативной памяти {ram_gb:.1f} ГБ, а нужно минимум {MIN_RAM_GB}. "
                           "Mico AI будет работать медленно и может тормозить."))
    if free_gb is None:
        out.append((None, "Свободное место на диске не удалось проверить."))
    elif free_gb >= MIN_DISK_GB:
        out.append((True, f"Свободного места на диске {free_gb:.0f} ГБ (нужно около {MIN_DISK_GB})."))
    else:
        out.append((False, f"Свободного места на диске {free_gb:.0f} ГБ, а нужно около {MIN_DISK_GB}. "
                           "Освободи место: «что занимает место»."))
    if not installed:
        out.append((None, "Модели не проверить: движок не отвечает. Перезапусти Mico AI и повтори включение."))
    else:
        for label, name in (("Модель для общения", cfg.get("text_model")),
                            ("Модель для экрана", cfg.get("vision_model"))):
            if _has_model(name, installed):
                out.append((True, f"{label} скачана: {name}."))
            else:
                out.append((False, f"{label} не скачана: {name}. Скачай её в ⚙ Настройки → Модели."))
    if not int(cfg.get("sleep_after_min", sleepmode.DEFAULT_MINUTES) or 0):
        out.append((False, "Mico AI не засыпает: он будет всё время на экране. Задай время сна в ⚙ Настройки → Поведение."))
    return out


def checkup_lines(cfg, installed, ram_gb, free_gb):
    """То же, что checkup, но готовым текстом с метками: ✅ ⚠️ ℹ️."""
    mark = {True: "✅", False: "⚠️", None: "ℹ️"}
    return [f"{mark[ok]} {text}" for ok, text in checkup(cfg, installed, ram_gb, free_gb)]


# ----- Mico AI: состояния полоски, тишина, системные проверки, приветствие, быстрые действия -----
SESSION_SEC = 30 * 60                    # Mico AI помнит тему разговора дольше обычного: 30 минут
STATE_NAMES = {                          # названия действий для полоски (как видит пользователь)
    "listen": "Ждёт", "think": "Думает", "break": "Перерыв",
    "watch": "Наблюдение", "tip": "Подсказка", "warn": "Предупреждение",
}
DEFAULT_COLORS = {                       # по умолчанию у каждого действия свой цвет — иначе их не различить
    "listen": "#FFCFA3",                 # ждёт — тёплый цвет Mico AI
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


# Быстрые действия (⚡ под строкой ответа): группы, у каждого действия иконка, название и фраза.
# Фразы — те же, что Mico AI уже понимает (см. chips.py), поэтому кнопка всегда что-то делает.
QUICK_GROUPS = [
    ("Экран и работа", [
        ("📸", "Скриншот", "сделай скриншот"),
        ("👀", "Что на экране", "что у меня на экране?"),
        ("🕐", "Что я делал", "что я делал час назад?"),
        ("⏰", "Таймер 10 мин", "поставь таймер на 10 минут"),
    ]),
    ("Звук и экран", [
        ("🔇", "Без звука", "выключи звук"),
        ("🔉", "Тише", "тише"),
        ("🔊", "Громче", "громче"),
        ("🌙", "Тёмная тема", "включи тёмную тему"),
        ("☀️", "Светлая тема", "включи светлую тему"),
        ("🔔", "Не беспокоить", "включи не беспокоить"),
    ]),
    ("Музыка и питание", [
        ("⏯", "Пауза", "пауза"),
        ("⏭", "Трек дальше", "переключи трек"),
        ("🔋", "Заряд батареи", "заряд батареи"),
    ]),
    ("Система", [
        ("📈", "Нагрузка ПК", "что грузит процессор"),
        ("💽", "Место", "сколько места на диске"),
        ("📊", "Диспетчер", "открой диспетчер задач"),
        ("🔄", "Обновления", "проверь обновления"),
        ("🔒", "Блокировка", "заблокируй пк"),
    ]),
]
QUICK_ACTIONS = [(title, phrase) for _group, items in QUICK_GROUPS for _emoji, title, phrase in items]


def glow_on(cfg):
    """Подсветка кнопок (при наведении и в быстрых действиях). Выключена — кнопки ровные, без акцентного свечения."""
    return bool(cfg.get("button_glow", True))


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
    """Приветствие в Mico AI — строка над Mico AI: первая фраза приветствия и первая строка итога дня."""
    first = " ".join(str(hello_text or "").split())
    first = first.split(". ")[0].split("! ")[0].strip()
    summary = " ".join(str(summary_text or "").split())
    line = first + (" Итог: " + summary if summary else "")
    return subtitle_text(line, limit)


# ----- Mico AI: толщина полоски, волны при ответе, переход, тур, моргание (чистая логика) -----
THICK_MIN, THICK_MAX, THICK_DEFAULT = 2, 24, 4     # толщина полоски, px: тоньше — не видно, толще — мешает
WAVE_SOURCES = {                                    # откуда цвет волн: из персонализации Mico AI, цвета действия, свой или набор
    "mico": "Цвет Mico AI (из персонализации)",
    "state": "Цвет действия",
    "custom": "Свой цвет",
    "theme": "Готовый набор",
}
# Готовые наборы волн: несколько цветов, которые плавно сменяют друг друга, пока волна бежит.
WAVE_THEMES = {
    "sunset": ("Закат", ["#FF9F6B", "#FFCFA3", "#FF7EB6"], {
        "listen": "#FFCFA3", "think": "#FF9F6B", "break": "#FFD27F",
        "watch": "#FF7EB6", "tip": "#FFB38A", "warn": "#FF6B6B"}),
    "ocean": ("Океан", ["#7FB8FF", "#9FD3FF", "#5EE0D0"], {
        "listen": "#9FD3FF", "think": "#7FB8FF", "break": "#5EE0D0",
        "watch": "#B8C8FF", "tip": "#A8F0FF", "warn": "#FF8FA3"}),
    "mint": ("Мята", ["#9BE3A8", "#7FE0C0", "#C6F6A8"], {
        "listen": "#C6F6A8", "think": "#9BE3A8", "break": "#7FE0C0",
        "watch": "#E0F08A", "tip": "#8FF0D8", "warn": "#FF9F9F"}),
    "lavender": ("Лаванда", ["#D6B8FF", "#B9A0FF", "#FFB8E6"], {
        "listen": "#E6D4FF", "think": "#B9A0FF", "break": "#FFB8E6",
        "watch": "#8FA8FF", "tip": "#C7F0FF", "warn": "#FF9FC8"}),
}
WAVE_THEME_DEFAULT = "sunset"


def theme_states(key):
    """Цвета шести действий под выбранный набор. Неизвестный набор — стандартные цвета."""
    entry = WAVE_THEMES.get(str(key))
    if not entry or entry[2] is None:
        return dict(DEFAULT_COLORS)
    return dict(entry[2])

WAVE_DEFAULT_CUSTOM = "#FFCFA3"
TOUR = [                                            # что Mico AI рассказывает сразу после включения Mico AI, по одной строке
    "Я теперь внизу по центру экрана — там, где меня видно и где я никому не мешаю.",
    "Полоска по краю показывает, чем я занят: жду, думаю, напоминаю о перерыве. Цвет каждого действия можно выбрать.",
    "Когда я отвечаю, полоска слегка волнуется — так видно, что я работаю.",
    "Ctrl+Alt+S — «что на экране?»: я посмотрю на экран и коротко скажу главное. "
    "Ctrl+Alt+H — помогу с программой, которой ты пользуешься сейчас.",
    "Короткий ответ появится строкой надо мной. Длинный сам откроет этот чат, чтобы его было удобно читать.",
    "Если ты меня долго не трогаешь, я плавно уплываю вниз и растворяюсь. Вернуть меня можно вопросом или горячей клавишей.",
]
TOUR_GAP_MS = 1500                                   # пауза между строками тура: как будто печатаю
EDGE_SWEEP_SEC = 0.8                                 # свечение и капсула появляются плавно
STATE_TEXT = {                                       # короткая строка рядом с Mico AI: что он делает сейчас
    "listen": "жду", "think": "думаю…", "break": "пора отдохнуть",
    "watch": "вижу", "tip": "совет", "warn": "внимание",
}


def glow_height(cfg):
    """Высота свечения внизу экрана, px: тонкое — 48, толстое — до 180. По умолчанию — около 88."""
    return 48 + thickness(cfg) * 10                                        # небольшое скругление углов полоски по краям экрана, px
ARRIVE_SEC = 0.42                                    # Mico AI выезжает из угла в центр внизу
LEAVE_SEC = 0.35                                     # и уезжает обратно, когда Mico AI выключили
SLEEP_DROP_PX = 90                                   # во сне Mico AI уходит вниз на столько пикселей
TAP_WINDOW_SEC = 2.5                                 # нажатия по Mico в голосовом режиме считаем за это время
TAP_LIMIT = 5                                        # столько нажатий подряд — Mico просит не спешить
TAP_WARN_GAP_SEC = 12                                # просьбу повторяем не чаще, чем раз в это время
TAP_WARNING = "Эй, не так быстро! Я чувствительный, нажимай, пожалуйста, помедленнее."
SCREEN_HIDE_MS = 320                                 # сколько ждём, пока Mico уйдёт с экрана, прежде чем снимать экран
SCREEN_MAX_WAIT_MS = 90000                           # если ответа на «что на экране» так долго нет — Mico всё равно вернётся
SCREEN_TALK_SEC = 90                                 # после вопроса про экран следующие вопросы в голосовом режиме тоже про экран
SCREEN_FOLLOW_PROMPT = ("На картинке — экран пользователя прямо сейчас. Если вопрос про него — ответь по картинке, "
                        "коротко и по делу. Если вопрос не про экран — ответь обычно и картинку не упоминай.\n\nВопрос: {question}")
_SCREEN_WORDS = re.compile(r"экран|окн|здесь|тут|вот|этот|эта|\bэто\b|картин|скрин|написан|видиш|посмотри|прочитай|что за|что там|на что", re.I)


def is_screen_followup(text):
    """Вопрос похож на вопрос про то, что видно на экране («что здесь написано», «это что»)."""
    return bool(_SCREEN_WORDS.search(text or ""))


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


GLOW_EDGES = "edges"                       # нежные полоски вдоль низа, боков и верха, как у Apple Intelligence
GLOW_STYLES = (GLOW_EDGES,)
GLOW_DEFAULT = GLOW_EDGES                  # волны внизу экрана убраны: подсветка всегда полосками по краям


def glow_style(cfg):
    """Подсветка всегда в виде полосок по краям. Старые настройки с волнами игнорируются."""
    return GLOW_EDGES


WAVE_HEIGHT_MIN, WAVE_HEIGHT_MAX, WAVE_HEIGHT_DEFAULT = 30, 200, 100   # толщина волн, % от стандартной


def wave_height(cfg):
    """Толщина (высота) волн в процентах от стандартной: 100 — как было. Мусор — стандартная."""
    try:
        v = int(round(float(cfg.get("wi_wave_height", WAVE_HEIGHT_DEFAULT))))
    except (TypeError, ValueError):
        v = WAVE_HEIGHT_DEFAULT
    return max(WAVE_HEIGHT_MIN, min(WAVE_HEIGHT_MAX, v))


def glow_visible(cfg):
    """Подсветка видна постоянно: в виде волн или полосок. Без неё режим Mico AI работает, но экран не подсвечен."""
    return glow_style(cfg) == GLOW_EDGES or waves_on(cfg)


EDGE_W_MIN, EDGE_W_MAX, EDGE_W_DEFAULT = 6, 120, 48    # толщина полосок по краям, px


def edge_band(cfg):
    """Ширина полосок у края экрана, px — своя настройка «Толщина полосок по краям»."""
    try:
        v = int(round(float(cfg.get("wi_edge_width", EDGE_W_DEFAULT))))
    except (TypeError, ValueError):
        v = EDGE_W_DEFAULT
    return max(EDGE_W_MIN, min(EDGE_W_MAX, v))


def edge_alpha(cfg=None):
    """Полоски по краям всегда в полную силу: прозрачности нет."""
    return 1.0


def wave_color(cfg, state):
    """Цвет волн: по выбору пользователя — цвет Mico AI из персонализации, цвет действия или свой."""
    src = cfg.get("wi_wave_source", "mico")
    if src == "custom" and _HEX.fullmatch(str(cfg.get("wi_wave_custom", ""))):
        return str(cfg["wi_wave_custom"]).upper()
    if src == "mico" and _HEX.fullmatch(str(cfg.get("color", ""))):
        return str(cfg["color"]).upper()
    if src == "theme":
        return theme_colors(cfg)[0].upper()
    return state_color(cfg, state)


def plain_from_html(h):
    """Ответ в виде карточек или списка — в обычный текст для чата Mico AI. Пустой результат — короткая подсказка."""
    t = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</tr>|</div>|</h\d>", "\n", str(h or ""))
    t = re.sub(r"<[^>]+>", "", t)
    import html as _html
    t = _html.unescape(t)
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    out = "\n".join(lines)[:1500]
    return out or "Ответ оформлен карточками — полностью он виден в обычном окне Mico."


def theme_colors(cfg, hour=None):
    """Список цветов выбранного набора. Неизвестный набор (в том числе старое «по времени суток») — набор по умолчанию.
    hour больше не используется; параметр оставлен, чтобы старые вызовы не сломались."""
    key = str(cfg.get("wi_wave_theme", WAVE_THEME_DEFAULT))
    if key not in WAVE_THEMES or WAVE_THEMES[key][1] is None:
        key = WAVE_THEME_DEFAULT
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
    """Сколько Mico AI «говорит» ответ: как долго идёт тот самый разговор и волны на полоске."""
    return max(1.5, min(12.0, 0.028 * len(" ".join(str(text or "").split()))))


def tour_lines(checkup_lines=()):
    """Тур по Mico AI: фразы по порядку. Если есть проверка при включении — она последней строкой."""
    lines = list(TOUR)
    if checkup_lines:
        lines.append("Проверка при включении:\n" + "\n".join(checkup_lines))
    return lines


# ----- Mico AI: помощник по буферу, реакция на ошибки, файлы (тексты запросов и подписи) -----
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


# ----- Mico AI: тихий час, «не беспокоить», короче/подробнее, чат с файлом, загрузка -----
DND_CHOICES = [(30, "На 30 минут"), (60, "На час"), (120, "На два часа"), (0, "Выключить")]
FILE_TTL_SEC = 30 * 60                     # файл помним в чате Mico AI полчаса без новых вопросов
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
