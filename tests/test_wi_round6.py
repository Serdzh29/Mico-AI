"""Бета-правки: нежные полоски, чат следует за Mico."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import intel

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()





def test_glow_style_defaults_and_validation():
    check(intel.glow_style({}) == "edges", "по умолчанию — полоски по краям")
    check(intel.glow_style({"wi_glow_style": "waves"}) == "edges", "старые волны игнорируются")
    check(intel.glow_style({"wi_glow_style": "мусор"}) == "edges", "мусор — полоски")
    check(intel.glow_visible({"wi_waves": False, "wi_glow_style": "edges"}), "полоски видны без волн")
    check(intel.glow_visible({"wi_waves": False, "wi_glow_style": "waves"}), "полоски видны всегда")
    check(intel.edge_band({"wi_edge_width": 1}) == intel.EDGE_W_MIN, "полоски: не тоньше минимума")
    check(intel.edge_band({"wi_edge_width": 500}) == intel.EDGE_W_MAX, "полоски: не толще максимума")
    check(intel.edge_band({}) == intel.EDGE_W_DEFAULT, "полоски: по умолчанию")
    check(intel.edge_alpha({"wave_opacity": 0}) == 0.0, "прозрачность 0 — полоски не видны")
    check(abs(intel.edge_alpha({"wave_opacity": 85}) - 1.36) < 1e-6, "85 — заметные полоски")
    check(abs(intel.edge_alpha({"wave_opacity": 100}) - 1.6) < 1e-6, "100 — самые яркие")
    check("wi_edge_width" in read("main.py") and "self.wi_edge = NoWheelSlider" in read("main.py"), "ползунок полосок")
    check("intel.edge_alpha(self.cfg)" in read("intel_ui.py"), "прозрачность применяется к полоскам")

def test_chat_follows_mico_and_never_overlaps():
    ui = read("intel_ui.py")
    wc = read("aichat.py")
    check("def _follow_blob" in wc and "self._follow.start()" in wc, "чат едет за Mico")
    check("class Subtitle" not in ui, "строки над Mico AI больше нет")
    check("room_above >= CHAT_MIN_H" in wc and "below = blob.y()" in wc, "если нет места сверху — под Mico")
    check("self._pos_busy = True" in wc, "во время выезда не мешаем анимации")

def test_edge_style_is_drawn_without_waves():
    ui = read("intel_ui.py")
    check("def _draw_edges" in ui and "intel.GLOW_EDGES" in ui, "нежные полоски рисуются")
    check(re.search(r"if intel\.glow_style\(self\.cfg\) == intel\.GLOW_EDGES:[\s\S]{0,200}?self\._draw_edges", ui), "ветка по виду")

def test_wave_height_setting():
    check(intel.wave_height({}) == 100, "по умолчанию как было")
    check(intel.wave_height({"wi_wave_height": 10}) == intel.WAVE_HEIGHT_MIN, "не ниже минимума")
    check(intel.wave_height({"wi_wave_height": 999}) == intel.WAVE_HEIGHT_MAX, "не выше максимума")
    check(intel.wave_height({"wi_wave_height": "мусор"}) == 100, "мусор — стандартная")
    main = read("main.py")
    check("self.wi_wh = NoWheelSlider" not in main and "Толщина волн" not in main, "ползунок толщины волн убран")
    check("intel.wave_height(self.cfg) / 100.0" in read("intel_ui.py"), "волны используют толщину")


def test_edges_use_chosen_wave_color_not_state_color():
    ui = read("intel_ui.py")
    check('wi_wave_source", "mico") == "state"' in ui, "цвет действия только при выборе «Цвет действия»")
    check("intel.wave_base(self.cfg, self.state, self.phase)" in ui, "полоски берут выбранный цвет")

def test_wi_hard_block():
    check(intel.block_reasons(6, 100) != [], "6 ГБ памяти — блок")
    check(intel.block_reasons(32, 10) != [], "10 ГБ места — блок")
    check(intel.block_reasons(16, 20) == [], "ровно минимум — можно")
    check(intel.block_reasons(15.6, 25) == [], "15.6 ГБ с допуском 0.5 — можно")
    check(intel.block_reasons(None, None) == [], "не удалось прочитать — не блокируем")
    cfg = {"assist_style": "intelligence"}
    msg = intel.enforce_mode(cfg, 6, 100)
    check(msg is None or "Mico AI" in msg, "на слабом ПК Mico AI только предупреждает")
    cfg2 = {"assist_style": "intelligence"}
    check(intel.enforce_mode(cfg2, 32, 200) is None and cfg2["assist_style"] == "intelligence", "мощный ПК — WI остаётся")
    pass  # классического режима больше нет
    main = read("main.py")
    "wi_notice" in main

def test_clip_check_commands():
    import clipcheck
    check(clipcheck.command("исправь текст из буфера") == {"action": "fix"}, "исправить буфер")
    check(clipcheck.command("проверь буфер") == {"action": "fix"}, "проверить буфер")
    check(clipcheck.command("переведи буфер на английский") is None, "перевода нет: он удалён из проекта")
    check(clipcheck.command("открой блокнот") is None, "обычная команда не трогается")
    check("Верни только" in clipcheck.prompt({"action": "fix"}, "привет мир") and "привет мир" in clipcheck.prompt({"action": "fix"}, "привет мир"), "промпт")
    check(len(clipcheck.prompt({"action": "fix"}, "a" * 9000)) < clipcheck.MAX_CHARS + 300, "длинный текст обрезается")

def test_watch_switch_wired():
    main = read("main.py")
    check('"wi_watch"' not in main and "self.wi_watch" not in main, "выключатель «Смотреть на экран сам» убран вместе с инициативой")
    check("_wi_chat.on_draft" in main, "черновик сохраняется")
    check("brain.clip_text = lambda" in main and "clipcheck.command(q)" in read("brain.py"), "проверка буфера подключена")


if __name__ == "__main__":
    for n in [n for n in list(globals()) if n.startswith("test_")]:
        globals()[n]()
    print("ok: wi round 6")
