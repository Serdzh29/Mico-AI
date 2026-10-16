"""Бета-правки: слова пробуждения, выбор моделей Vosk, нежные полоски, чат следует за Mico."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import voice as V, voicemodel, intel

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

def test_wake_words_are_fixed():
    check(V.WAKE_WORDS == ("мико", "mico"), "только мико и mico")
    check(V.wake_words_from("что угодно, микро") == ("мико", "mico"), "настройка слов не меняет список")
    check(V.wake_words_from("") == ("мико", "mico"), "пусто — тот же список")

def test_wake_setting_field_is_gone():
    main = read("main.py")
    check("self.vwords" not in main, "поле слов убрано из настроек")
    check("Слова пробуждения (через запятую)" not in main, "подпись поля убрана")
    check("\"wake_words\": \"" in main, "ключ сохранён для совместимости")
    check("\"wake_words\"" not in read("settings_info.py"), "подсказка к полю убрана")

def test_vosk_catalog_has_three_models():
    names = list(voicemodel.MODELS)
    check(names[0] == voicemodel.DEFAULT_MODEL, "первая — по умолчанию")
    check(len(names) == 3, "три размера модели")
    check(all(voicemodel.MODELS[n]["url"].startswith("https://alphacephei.com/vosk/models/") for n in names), "адреса")
    check(voicemodel.model_name_of("нет-такой") == voicemodel.DEFAULT_MODEL, "неизвестная — по умолчанию")
    check(voicemodel.default_dir("/x", "vosk-model-ru-0.42").endswith("vosk-model-ru-0.42"), "папка по имени модели")

def test_vosk_catalog_is_in_settings():
    main = read("main.py")
    check("self.model_pick = NoWheelComboBox()" in main, "выбор модели в настройках")
    check("vosk_model_name=self.model_name_value" in main, "выбор сохраняется")
    check("voicemodel.fetch_model(APPDIR, progress=prog, name=name)" in main, "скачивается выбранная модель")

def test_glow_style_defaults_and_validation():
    check(intel.glow_style({}) == "waves", "по умолчанию — волны")
    check(intel.glow_style({"wi_glow_style": "edges"}) == "edges", "полоски")
    check(intel.glow_style({"wi_glow_style": "мусор"}) == "waves", "мусор — волны")
    check(intel.glow_visible({"wi_waves": False, "wi_glow_style": "edges"}), "полоски видны без волн")
    check(not intel.glow_visible({"wi_waves": False, "wi_glow_style": "waves"}), "волны выключены — не видны")
    check(intel.edge_band({"wi_edge_width": 1}) == intel.EDGE_W_MIN, "полоски: не тоньше минимума")
    check(intel.edge_band({"wi_edge_width": 500}) == intel.EDGE_W_MAX, "полоски: не толще максимума")
    check(intel.edge_band({}) == intel.EDGE_W_DEFAULT, "полоски: по умолчанию")
    check(intel.edge_alpha({"wave_opacity": 0}) == 0.0, "прозрачность 0 — полоски не видны")
    check(abs(intel.edge_alpha({"wave_opacity": 85}) - 1.02) < 1e-6, "85 — как по умолчанию")
    check("wi_edge_width" in read("main.py") and "self.wi_edge = NoWheelSlider" in read("main.py"), "ползунок полосок")
    check("intel.edge_alpha(self.cfg)" in read("intel_ui.py"), "прозрачность применяется к полоскам")

def test_chat_follows_mico_and_never_overlaps():
    ui = read("intel_ui.py")
    wc = read("wichat.py")
    check("def _follow_blob" in wc and "self._follow.start()" in wc, "чат едет за Mico")
    check("def _keep_near" in ui and "self._follow.start()" in ui, "строка держится над Mico")
    check("room_above >= CHAT_MIN_H" in wc and "below = blob.y()" in wc, "если нет места сверху — под Mico")
    check("self._pos_busy = True" in wc, "во время выезда не мешаем анимации")

def test_edge_style_is_drawn_without_waves():
    ui = read("intel_ui.py")
    check("def _draw_edges" in ui and "intel.GLOW_EDGES" in ui, "нежные полоски рисуются")
    check(re.search(r"if intel\.glow_style\(self\.cfg\) == intel\.GLOW_EDGES:\s+self\._draw_edges", ui), "ветка по виду")

def test_wave_height_setting():
    check(intel.wave_height({}) == 100, "по умолчанию как было")
    check(intel.wave_height({"wi_wave_height": 10}) == intel.WAVE_HEIGHT_MIN, "не ниже минимума")
    check(intel.wave_height({"wi_wave_height": 999}) == intel.WAVE_HEIGHT_MAX, "не выше максимума")
    check(intel.wave_height({"wi_wave_height": "мусор"}) == 100, "мусор — стандартная")
    main = read("main.py")
    check('"wi_wave_height"' in main and "self.wi_wh = NoWheelSlider" in main, "ползунок в настройках WI")
    check("intel.wave_height(self.cfg) / 100.0" in read("intel_ui.py"), "волны используют толщину")

def test_voice_reports_model_loading_and_ready():
    voice = read("voice.py")
    check("on_status=None" in voice and "Загружаю модель" in voice, "статус загрузки модели")
    check("Голос готов" in voice, "статус готовности")
    check("on_status=self.voice_status.emit" in read("main.py") and "self.voice_status.connect(self.say)" in read("main.py"),
          "статусы попадают в чат")

def test_edges_use_chosen_wave_color_not_state_color():
    ui = read("intel_ui.py")
    check('wi_wave_source", "mico") == "state"' in ui, "цвет действия только при выборе «Цвет действия»")
    check("intel.wave_base(self.cfg, self.state, self.phase)" in ui, "полоски берут выбранный цвет")

if __name__ == "__main__":
    for n in [n for n in list(globals()) if n.startswith("test_")]:
        globals()[n]()
    print("ok: wi round 6")
