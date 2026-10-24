"""Режим Windows Intelligence: расчёты без Qt — где Mico, как светится полоса, что пишем в строке над ним."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import intel
import sleepmode


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_style_defaults_to_classic():
    check(intel.style_of(None) == intel.INTELLIGENCE and intel.style_of("что-то") == intel.INTELLIGENCE, "один режим: Mico AI")
    check(intel.style_of("intelligence") == intel.INTELLIGENCE)


def test_intelligence_puts_mico_at_bottom_center_and_classic_keeps_choice():
    check(intel.placement_for("intelligence", "tl") == sleepmode.SPOT, "в режиме Intelligence — внизу по центру")
    check(intel.placement_for("classic", "tl") != "tl", "один режим: Mico внизу по центру")
    check(intel.placement_for("classic", "manual") != "manual", "один режим: Mico внизу по центру")


def test_bottom_center_spot_is_centered_and_above_the_edge():
    avail = (0, 0, 1920, 1040)                                  # без панели задач
    x, y = sleepmode.corner_spot(avail, 200, sleepmode.SPOT)
    check(abs((x + 100) - 960) <= 1, f"по центру: {x}")
    check(y + 200 <= 1040 and y > 700, f"внизу, у края: {y}")
    check(sleepmode.home_corner(False, sleepmode.SPOT, None) == sleepmode.SPOT, "домашнее место — внизу по центру")
    check(sleepmode.home_corner(True, sleepmode.SPOT, "br") == sleepmode.SPOT, "во сне — внизу по центру")




def test_approach_converges_and_snaps():
    v, steps = 0.0, 0
    while v < 1.0 and steps < 500:
        v, steps = intel.approach(v, 1.0), steps + 1
    check(v == 1.0 and steps < 100, "доходит до цели и защёлкивается")
    check(intel.approach(1.0, 0.0) < 1.0, "гаснет")


def test_subtitle_is_short_and_readable():
    check(intel.subtitle_text("  много\n\n  пробелов  ") == "много пробелов")
    long = "слово " * 100
    s = intel.subtitle_text(long)
    check(len(s) <= intel.SUBTITLE_MAX and s.endswith("…"), "длинный ответ обрезается")


def test_wiring_is_in_place():
    main = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    ui = open(os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    blob = open(os.path.join(ROOT, "blob.py"), encoding="utf-8").read()
    check('"assist_style"' in main and "intel_ui.Intel(" in main, "настройка и подключение")
    check("panel.busy_changed.connect(intel_ctl.busy)" in main and "panel.user_sent.connect(intel_ctl.wi_user)" in main
          and "panel.mico_said.connect(intel_ctl.wi_mico)" in main, "сигналы чата WI")
    check("self.assist" not in main, "переключателя режима в настройках больше нет")
    check("WindowTransparentForInput" in ui, "полоса не мешает кликам")
    check("self.placement()" in blob and "intel.placement_for" in blob, "Mico встаёт внизу по центру")

def test_long_answer_opens_chat_instead_of_subtitle():
    check(not intel.opens_chat("а" * 200), "ровно 200 знаков — ещё строкой")
    check(intel.opens_chat("а" * 201), "больше 200 — открываем чат")
    check(intel.opens_chat("  " + "слово " * 60), "пробелы не считаются")
    check(not intel.opens_chat("коротко"), "короткий — строкой")


def test_tour_explains_the_mode_and_its_advantages():
    text = " ".join(intel.TOUR)
    check(len(intel.TOUR) >= 5, "тур идёт по строкам, а не одним куском")
    for word in ("внизу по центру", "полоска", "Ctrl+Alt+S", "Ctrl+Alt+H", "растворяюсь", "волнуется"):
        check(word in text, word)


def test_sleep_in_intelligence_moves_down_and_shrinks_not_fades():
    main_blob = open(os.path.join(ROOT, "blob.py"), encoding="utf-8").read()
    ui = open(os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    check("corner = sleepmode.home_corner(self.asleep, self.placement(), self.cfg.get(\"sleep_corner\"))" in main_blob,
          "во сне Mico едет к своему месту")
    check("def on_sleep" in ui and "self.aichat.dismiss()" in ui, "во сне чат уходит")
    check("def vanish" not in main_blob, "растворения больше нет: Mico виден и уменьшен")


def test_wi_only_questions_are_routed_correctly():
    import re
    check(re.search(r"скриншот|скрин\b|снимок экрана", intel.SCREEN_QUESTION), "«Что на экране?» идёт в ветку скриншота")
    check("«" not in intel.window_question(""), "без названия — общий вопрос")
    q = intel.window_question("  Блокнот  — документ.txt  ")
    check("«Блокнот — документ.txt»" in q, q)
    check(len(intel.window_question("я" * 500)) < 200, "длинное название обрезается")
    check(intel.SCREEN_KEY != intel.WINDOW_KEY and intel.SCREEN_KEY != "ctrl+alt+m", "сочетания не совпадают с чатом")


def test_checkup_reports_ram_disk_and_both_models():
    cfg = {"sleep_after_min": 3, "text_model": "qwen2.5:7b", "vision_model": "qwen2.5vl:7b"}
    good = intel.checkup(cfg, ["qwen2.5:7b", "qwen2.5vl:latest"], 32.0, 120.0)
    check(all(ok is True for ok, _ in good[:-1]), good)              # всё в порядке, кроме последней заметки
    bad = intel.checkup(cfg, ["qwen2.5:7b"], 8.0, 5.0)
    oks = [ok for ok, _ in bad]
    check(oks[0] is False and oks[1] is False, "мало памяти и места — предупреждаем")
    check(any("Модель для экрана не скачана" in t for _, t in bad), "не хватает модели для экрана")
    check(any("Модель для общения скачана" in t for _, t in bad), "общая модель есть — так и пишем")


def test_ram_tolerance_and_unknown_values():
    cfg = {"sleep_after_min": 3, "text_model": "a", "vision_model": "b"}
    ok16 = intel.checkup(cfg, ["a", "b"], 15.6, 50.0)[0]
    check(ok16[0] is True, "15.6 ГБ — это 16 ГБ по версии Windows")
    unknown = intel.checkup(cfg, [], None, None)
    check(all(ok is None for ok, _ in unknown[:4]), "что не прочитали — честно None")
    check(any("движок не отвечает" in t for _, t in unknown), "без Ollama модели не проверить")


def test_checkup_lines_have_marks_and_sleep_warning():
    cfg = {"sleep_after_min": 0, "text_model": "a", "vision_model": "b"}
    lines = intel.checkup_lines(cfg, ["a", "b"], 32.0, 100.0)
    check(lines[0].startswith("✅"), lines[0])
    check(any(l.startswith("⚠️") and "не засыпает" in l for l in lines), lines)
    check(not any("нагружает" in l or "сам смотрю на экран" in l for l in lines), "строки про нагрузку от экрана больше нет")


def test_gate_message_explains_how_to_enable():
    check("Mico AI" in intel.GATE_TEXT, intel.GATE_TEXT)


def test_wi_hotkeys_and_buttons_are_wired():
    main = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    ui = open(os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    check("2: cfg.get(\"hotkey_screen\"" in main and "3: cfg.get(\"hotkey_window\"" in main, "сочетания WI")
    check("intel_ctl.screen_hotkey()" in main and "intel_ctl.window_hotkey(active_title())" in main, "обработчики")
    check("intel.checkup_lines(cfg, list_models()" in main and "total_ram_gb()" in main, "проверка при запуске")
    check("class Subtitle" not in ui and "class QuickPanel" not in ui, "быстрый чат удалён полностью")
    check("toggle_quick" not in main and "toggle_quick" not in ui, "F8 больше не открывает быстрый чат")
    check("def gate(self)" in ui and "def retry(self)" in ui, "гейт и повтор")


def test_fullscreen_detection_has_a_tolerance():
    mon = (0, 0, 1920, 1080)
    check(intel.is_fullscreen((0, 0, 1920, 1080), mon), "игра на весь экран")
    check(intel.is_fullscreen((1, 0, 1919, 1081), mon), "допуск в пару пикселей")
    check(not intel.is_fullscreen((0, 40, 1920, 1080), mon), "окно с панелью задач — не полный экран")
    check(not intel.is_fullscreen(None, mon), "неизвестно — не полный экран")


def test_problems_only_when_it_matters():
    check(intel.problems(50, 40, 80, True) == [], "всё в порядке — молчим")
    keys = [k for k, _ in intel.problems(3.2, 95, 10, False)]
    check(keys == ["disk", "mem", "battery"], keys)
    check("battery" not in [k for k, _ in intel.problems(None, None, 5, True)], "от зарядки батарея не в счёт")
    check(intel.problems(None, None, None, None) == [], "нет данных — ничего не выдумываем")


def test_warnings_are_not_repeated_within_two_hours():
    last = {}
    check(intel.warn_due("disk", 1000, last), "первый раз — можно")
    last["disk"] = 1000
    check(not intel.warn_due("disk", 1000 + 3600, last), "через час — ещё нельзя")
    check(intel.warn_due("disk", 1000 + intel.WARN_GAP_SEC, last), "через два часа — снова можно")


def test_each_notice_has_a_colour_and_the_states_are_known():
    for state in ("listen", "think", "break", "watch", "tip", "warn"):
        check(state in intel.STATE_COLORS, state)
    check(intel.STATE_COLORS["break"] != intel.STATE_COLORS["watch"] != intel.STATE_COLORS["warn"], "разные цвета")


def test_greeting_line_is_short_and_shows_the_summary():
    line = intel.greeting_line("Доброе утро! Как дела? Рад тебя видеть.", "Работал 3 ч, больше всего в браузере.")
    check(line.startswith("Доброе утро") and "Итог:" in line and len(line) <= intel.SUBTITLE_MAX, line)
    check(intel.greeting_line("Привет.", "") == "Привет.", "без итога — только приветствие")


def test_quick_actions_are_phrases_the_assistant_already_knows():
    check(len(intel.QUICK_ACTIONS) >= 4, "несколько действий")
    for title, phrase in intel.QUICK_ACTIONS:
        check(title and phrase and len(phrase) < 60, title)


def test_session_is_longer_than_default_memory():
    check(intel.SESSION_SEC >= 30 * 60, "WI помнит тему 30 минут")


def test_wi_features_are_in_the_code():
    main = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    ui = open(os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    check("panel.initiative.emit((msg, BREAK_MARK))" in main, "перерыв отправляется кортежем (исправлено падение)")
    check("self.intel.break_note(text)" in main and "self.intel.notify(text, \"watch\")" in main, "перерыв со сводкой, наблюдение отдельно")
    check("wi = intel_ctl.on()" not in main and "initiative_tick" not in main, "проверка экрана по инициативе убрана")
    check("def hushed(self)" in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "intel_ui.py"), encoding="utf-8").read(), "тишина (полноэкран, DND, тихий час) осталась в Intel")
    check('intel_ctl.greet(hello(), "")' in main, "приветствие строкой")
    check("fullscreen_now" in ui and "system_readings" in ui and "free_disk_gb" in ui, "тишина, ⚡ и проверки системы")
    check("dlg.window = max(normal, intel.SESSION_SEC)" in ui, "сессия дольше")


def test_default_colours_are_all_different():
    cols = list(intel.DEFAULT_COLORS.values())
    check(len(set(c.upper() for c in cols)) == len(cols), "у действий по умолчанию разные цвета")
    check(intel.DEFAULT_COLORS["listen"] != intel.DEFAULT_COLORS["think"], "ждёт и думает различимы")


def test_user_colours_are_checked_and_clashes_are_refused():
    ok = {"wi_colors": {"break": "#00FF00", "warn": "#FF0000"}}
    check(intel.state_colors(ok)["break"] == "#00FF00", "верный цвет принимаем")
    check(intel.state_colors(ok)["warn"] == "#FF0000", "второй верный цвет принимаем")
    dup = {"wi_colors": {"break": "#00FF00", "warn": "#00ff00"}}
    check(intel.state_colors(dup) == intel.DEFAULT_COLORS, "повтор цвета — возвращаем стандартные, не допускаем одинаковых")
    check(intel.state_colors({"wi_colors": {"break": "зелёный"}})["break"] == intel.DEFAULT_COLORS["break"],
          "не цвет — стандартный")
    check(intel.state_colors({"wi_colors": "мусор"}) == intel.DEFAULT_COLORS, "мусор в настройках — стандартные")
    cur = dict(intel.DEFAULT_COLORS)
    check(intel.color_clash(cur, "break", cur["watch"]) == "watch", "занятый цвет находим")
    check(intel.color_clash(cur, "break", cur["break"]) is None, "свой текущий цвет — не конфликт")
    check(intel.color_clash(cur, "break", "#123456") is None, "свободный цвет — можно")
    check(intel.state_color({"wi_colors": {"listen": "#112233"}}, "listen") == "#112233", "цвет действия из настроек")


def test_colour_settings_are_wired_into_the_glow_and_settings():
    main = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    ui = open(os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    check('"wi_colors": dict(intel.DEFAULT_COLORS)' in main, "цвета в настройках по умолчанию")
    check("_wi_colors_box(cfg), i18n.t(\"Полоска Mico AI\")" in main, "группа в настройках")
    check("Цвет занят" in main and "def _pick_wi" in main and "def _reset_wi_colors" in main, "проверка занятого цвета")
    check("intel.state_color(self.cfg, state)" in ui, "полоска берёт цвет из настроек")
    check("class QuickPanel" not in ui, "панель быстрых действий удалена вместе с быстрым чатом")


def test_intel_controller_timers_have_no_qobject_parent():
    # Intel — обычный класс, не QObject: QTimer(self) падает при запуске Mico (поймано у пользователя)
    ui = open(os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    body = ui[ui.index("class Intel:"):]
    check("QTimer(self)" not in body, "в Intel таймеры создаются без родителя-self")


def test_edge_strip_thickness_is_clamped_and_has_square_corners():
    check(intel.thickness({"wi_thickness": 99}) == intel.THICK_MAX, "толще максимума не даём")
    check(intel.thickness({"wi_thickness": 1}) == intel.THICK_MIN, "тоньше минимума не даём")
    check(intel.thickness({"wi_thickness": "x"}) == intel.THICK_DEFAULT, "мусор — стандартная")
    check(intel.thickness({}) == intel.THICK_DEFAULT and intel.THICK_MIN < intel.THICK_DEFAULT < intel.THICK_MAX)
    ui = open(os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    check("addRoundedRect" not in ui, "полоска по краю убрана, углов нет")
    check("QLinearGradient(QPointF(0, h), QPointF(0, h - bh))" not in ui, "волны внизу убраны")




def test_waves_take_the_chosen_colour_source():
    cfg = {"color": "#112233", "wi_wave_source": "mico", "wi_colors": {"listen": "#AABBCC"}}
    check(intel.wave_color(cfg, "listen") == "#112233", "волны — цвет Mico из персонализации")
    check(intel.wave_color(dict(cfg, wi_wave_source="state"), "listen") == "#AABBCC", "волны — цвет действия")
    check(intel.wave_color(dict(cfg, wi_wave_source="custom", wi_wave_custom="#ff0000"), "listen") == "#FF0000",
          "волны — свой цвет")
    check(intel.wave_color(dict(cfg, wi_wave_source="custom", wi_wave_custom="мусор"), "listen") == "#AABBCC",
          "неверный свой цвет — цвет действия")
    check(intel.waves_on({}) and not intel.waves_on({"wi_waves": False}), "волны включены по умолчанию")
    check(intel.hex_rgb("мусор") == intel.DEFAULT_ACCENT and intel.hex_rgb("#000000") == (0, 0, 0))
    check(intel.lerp_rgb((0, 0, 0), (255, 255, 255), 0) == (0, 0, 0) and intel.lerp_rgb((0, 0, 0), (255, 255, 255), 1) == (255, 255, 255))


def test_blink_is_smooth_and_eyes_open_again():
    check(intel.blink_close(0) == 0 and intel.blink_close(1) == 0, "в начале и в конце глаза открыты")
    check(intel.blink_close(0.5) > 0.99, "в середине моргания глаза почти закрыты")
    samples = [intel.blink_close(k / 50) for k in range(51)]
    check(max(abs(b - a) for a, b in zip(samples, samples[1:])) < 0.2, "моргание без резких скачков")
    check(intel.double_blink_close(0.0) == 0 and intel.double_blink_close(0.35) == 0 and intel.double_blink_close(0.15) > 0.9,
          "двойное моргание: два плавных прикрытия")
    blob = open(os.path.join(ROOT, "blob.py"), encoding="utf-8").read()
    check("blink = time.time() < self.blink_until" not in blob and "self.lid" in blob, "глаза идут через плавную открытость")


def test_speaking_waves_match_the_answer_length_and_tour_reads_checkup():
    check(1.5 <= intel.speak_seconds("да") <= 12 and intel.speak_seconds("x" * 5000) == 12, "волны — по длине ответа")
    lines = intel.tour_lines(["✅ память"])
    check(len(lines) == len(intel.TOUR) + 1 and "память" in lines[-1], "тур заканчивается проверкой")
    check(all(len(x) < 260 for x in intel.TOUR), "строки тура короткие и читаются")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
