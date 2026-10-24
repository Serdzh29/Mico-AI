"""Голосовой режим: микрофон в чате открывает отдельное окно с Mico. Внизу быстрая панель: экран, палитра,
микрофон, субтитры, настройки (голос и скорость) и крестик. Mico не засыпает, пока режим открыт.
Проверяется по исходникам (без Qt и микрофона), как остальные тесты голоса."""
import os as _os
import sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def block(src, start_marker, length=900):
    i = src.index(start_marker)
    return src[i:i + length]


def test_mic_in_chat_opens_separate_voice_window_and_collapses_chat():
    iu = read("intel_ui.py")
    check("self.aichat.listen.connect(self.enter_voice_mode)" in iu, "микрофон в чате открывает голосовой режим")
    body = block(iu, "    def enter_voice_mode(self):", 1300)
    check("self.aichat.dismiss()" in body, "чат сворачивается")
    check("self.voice_dock.show_stage(self.blob)" in body, "открывается отдельное окно, Mico переезжает в него")
    check("self.voice_dock.show_near" not in iu, "старой привязки кнопок под Mico больше нет")


def test_bottom_panel_buttons_in_order_and_wired():
    dock = read("voice_dock.py")
    order = [dock.index(f"self.{n} = self._button(") for n in
             ("mic_btn", "settings_btn", "palette_btn", "subs_btn", "exit_btn")]
    check(order == sorted(order), "порядок полоски: микрофон, голос и скорость, палитра, субтитры, завершить")
    check("screen_btn" not in dock and "screen_clicked" not in dock, "экрана в голосовом режиме нет")
    for sig in ("color_pick", "mute_clicked", "exit_clicked", "subs_toggled"):
        check(f"{sig} = pyqtSignal" in dock, sig)
    iu = read("intel_ui.py")
    for conn in ("self.voice_dock.color_pick.connect(self.blob.pick_color)",
                 "self.voice_dock.mute_clicked.connect(self._voice_mute_toggle)",
                 "self.voice_dock.exit_clicked.connect(self.exit_voice_mode)",
                 "self.voice_dock.subs_toggled.connect(self._voice_subs_toggle)"):
        check(conn in iu, conn)


def test_crossbar_is_minimal_and_has_no_separate_window_for_palette():
    dock = read("voice_dock.py")
    check("from aichat import _Palette" not in dock, "отдельного окна палитры нет")
    check("from onboarding import COLORS as PALETTE" in dock, "те же цвета, что в чате и при первом запуске")


def test_settings_section_has_voices_and_four_speeds():
    dock = read("voice_dock.py")
    check("def _toggle_settings" in dock and "_show_section" in dock, "настройки раскрываются в окне")
    check("voice_models.VOICES.items()" in dock, "голоса — из общего списка")
    for label in ('"0,5x"', '"1x"', '"1,5x"', '"2x"'):
        check(label in dock, label)
    for v in ("0.5", "1.0", "1.5", "2.0"):
        check(f"({v}," in dock, f"скорость {v}")
    check("self.voice_pick.emit(key)" in dock and "self.speed_pick.emit(float(value))" in dock,
          "выбор уходит наружу и сохраняется сразу")
    iu = read("intel_ui.py")
    check("self.voice_dock.voice_pick.connect(self._voice_pick)" in iu, "голос из панели — тот же выбор, что в чате")
    check("self.voice_dock.speed_pick.connect(self._voice_speed_pick)" in iu, "скорость сохраняется")
    check('self.cfg["voice_speed"] = float(speed)' in iu, "скорость пишется в настройки")
    check("if self.enabled() or self._session:" in read("voice_ctl.py"), "смена голоса в голосовом режиме применяется")


def test_palette_opens_inside_window_and_saves_color():
    dock = read("voice_dock.py")
    check("def _toggle_colors" in dock and "self._show_section(None if self.colors.isVisible() else self.colors)" in dock,
          "палитра раскрывается внутри окна, одновременно с настройками открыт только один раздел")
    check("self.color_pick.emit(hex_c)" in dock and "def _pick_color" in dock, "выбор цвета уходит в Mico")
    check("self.voice_dock.color_pick.connect(self.blob.pick_color)" in read("intel_ui.py"),
          "Mico крутится и меняет цвет (сохранение — через color_set в main)")


def test_subtitles_button_shows_speech_and_is_remembered():
    dock = read("voice_dock.py")
    check("def _toggle_subs" in dock and 'self.cfg["voice_subs"] = on' in dock, "кнопка включает субтитры и запоминает")
    check("self.cap_lbl.setText(text)" in dock and "_status" not in dock.split("def _show_mid")[1].split("def ")[0], "субтитры — плашка над полоской; статус не пишем в полоске")
    check('"subs": _subs' in read("uiicons.py"), "значок субтитров есть")
    check("def show_mico" in dock and "def show_user" in dock, "две строки: что говорит Mico и что спросили")
    check("_tail(text, SUB_CHARS)" in dock and "setWordWrap(True)" in dock, "показываем последние слова, переносим по строкам")
    iu = read("intel_ui.py")
    check("self.voice.sentence.connect(self.voice_dock.show_mico)" in iu, "субтитры — по фразе, которую Mico говорит")
    check("self.voice.said.connect(self.voice_dock.show_user)" in iu, "вопрос пользователя — в субтитрах")
    check("def _voice_subs_toggle" in iu and 'self.cfg["voice_subs"] = bool(on)' in iu, "выбор субтитров сохраняется")
    check("self.voice_dock.show_mico(emotions.split_mood(text)[1])" in block(iu, "    def answer(self, text):", 1800),
          "ответ попадает в субтитры до начала речи, без тегов настроения")
    vc = read("voice_ctl.py")
    check("sentence = pyqtSignal(str)" in vc and "self.sentence.emit(sent)" in vc, "фраза уходит в субтитры перед звуком")
    check(vc.index("self.sentence.emit(sent)") < vc.index("sd.play(audio, sr)"), "субтитры появляются вместе со звуком")


def test_voice_mode_has_no_screen_feature():
    iu = read("intel_ui.py")
    for gone in ("def _voice_screen(", "def _voice_screen_go(", "def _voice_screen_question(", "def _voice_back("):
        check(gone not in iu, gone)
    check("self.voice_dock.pause_for_capture" not in iu and "resume_after_capture" not in iu,
          "Mico больше не уходит на снимок экрана")
    check("self._voice_rearm)" in block(iu, "    def busy(self, on):", 700), "после ответа снова слушаем")


def test_mic_button_turns_listening_off_and_on():
    iu = read("intel_ui.py")
    body = block(iu, "    def _voice_mute_toggle(self):", 400)
    check("self.voice.set_muted(on)" in body and "self._voice_rearm()" in body, "выключить и снова включить")
    ui = read("uiicons.py")
    check('"mic_off": _mic_off' in ui, "значок выключенного микрофона")
    dock = read("voice_dock.py")
    check('"mic_off" if muted else "mic"' in dock, "значок меняется по состоянию")


def test_close_button_stops_everything_then_returns_chat():
    body = block(read("intel_ui.py"), "    def exit_voice_mode(self, to_text=False):", 1400)
    for must in ("self.voice.stop_speaking()", "self.voice.stop_listening()", "self.voice.set_session(False)",
                 "self.voice_dock.dismiss(return_to=rest, after=self._voice_gone)"):
        check(must in body, must)
    check("self.show_aichat()" in block(read("intel_ui.py"), "    def _voice_gone(self):", 200),
          "после возврата Mico открывается чат")


def test_voice_mode_blocks_sleep_until_it_is_left():
    main = read("main.py")
    i = main.index("blob.can_sleep = lambda:")
    check("intel_ctl.voice_mode" not in main[i:i + 400], "голосовой режим сам по себе не блокирует сон")
    iu = read("intel_ui.py")
    check("self.blob.keep_awake = False" in block(iu, "    def enter_voice_mode(self):", 600), "вход — Mico может уснуть в обводке")
    check("self.blob.keep_awake = on" in block(iu, "    def _voice_mute_toggle(self):", 400), "микрофон выключен — не спим")
    check("self.blob.keep_awake = False" in block(iu, "    def exit_voice_mode(self, to_text=False):", 1400), "выход — можно снова спать")
    check("self.blob.touch()" in block(iu, "    def enter_voice_mode(self):", 600), "вход — отсчёт сброшен")
    check("self.blob.touch()" in block(iu, "    def exit_voice_mode(self, to_text=False):", 1400), "выход — отсчёт начинается заново")
    check(read("sleepmode.py").count("def should_sleep") == 1, "сон решает одна функция")
    check("not self.can_sleep()" in read("blob.py"), "таймер сна учитывает can_sleep")
    blob = read("blob.py")
    check("if self.asleep or self.keep_awake:" in blob, "Mico не засыпает, пока держим keep_awake")
    check('if self.mood == "idle" and not self.keep_awake' in blob, "в голосовом режиме Mico не выглядит сонным")


def test_click_on_mico_does_not_open_chat_in_voice_mode():
    main = read("main.py")
    i = main.index("def _blob_clicked():")
    body = main[i:i + 500]
    check("intel_ctl.voice_mode" in body and "return" in body, "клик по Mico в голосовом режиме ничего не открывает")
    check("intel_ctl.toggle_aichat()" in body and "panel.toggle()" in body,
          "клик по Mico: режим Mico AI открывает его чат, иначе — обычный")
    check("blob.clicked.connect(_blob_clicked)" in main, "клик подключён к обработчику")


def test_answers_are_spoken_and_chat_stays_closed_in_voice_mode():
    iu = read("intel_ui.py")
    body = block(iu, "    def answer(self, text):", 1800)
    check("self.voice.enabled() or self.voice_mode" in body, "в голосовом режиме ответ говорим")
    check(body.index("if self.voice_mode:") < body.index("self.show_aichat(activate=False)"),
          "чат не открывается после ответа в голосовом режиме")


def test_voice_speaks_without_the_settings_checkbox():
    vc = read("voice_ctl.py")
    check("if not (self.enabled() or self._session):" in vc, "сеанс говорит даже при выключенной озвучке")
    check("self._session = bool(on)" in vc and "def set_session" in vc, "сеанс включается и выключается")


def test_listening_resumes_after_every_answer_and_not_while_thinking():
    iu = read("intel_ui.py")
    check("self.voice.speaking.connect(self._on_voice_speaking)" in iu, "после речи снова слушаем")
    check("self.voice.ready.connect(self._voice_rearm)" in iu, "когда модель загрузилась — слушаем")
    check("self.voice.stop_listening()" in block(iu, "    def busy(self, on):", 500), "пока думает — не слушаем")
    check("QTimer.singleShot(500, self._voice_rearm)" in iu, "если ответа нет — всё равно снова слушаем")
    vc = read("voice_ctl.py")
    body = block(vc, "    def begin_listening(self):", 500)
    check("self._muted or self._mode == \"cmd\" or self._speaking or self._stt is None" in body,
          "не открываем второй раз, не во время речи и без модели")


def test_rearm_after_failed_question_but_not_after_mic_failure():
    iu = read("intel_ui.py")
    check('startswith(("Не расслышал", "Не разобрал", "Голос не распознал"))' in iu,
          "вопрос не разобрали — снова слушаем")
    check('"Микрофон не' not in block(iu, "    def _voice_status(self, text):", 700).split("QTimer")[1],
          "если микрофон не открылся — не зацикливаемся")


def test_muted_microphone_is_really_off_for_wake_and_question():
    vc = read("voice_ctl.py")
    check("def _wake_active" in vc and "not self._muted" in vc, "выключенный микрофон не слушает «мико»")
    check("if self._muted and self._mode == \"cmd\":" in vc, "выключение отбрасывает записываемую фразу")
    check("want = self._wake_active()" in vc, "слушание «мико» следует за выключением")
    check("if self._muted:\n            self.status.emit(\"Микрофон выключен\")" in vc, "статус «выключен» виден")


def test_window_follows_mico_both_ways_and_stays_out_of_focus():
    dock = read("voice_dock.py")
    check("WA_ShowWithoutActivating" in dock, "окно не забирает фокус")
    check("self._follow.start()" in dock and "def _sync" in dock, "окно и Mico держатся вместе каждый кадр")
    check("self.move(self.pos() + b.pos() - self._expected)" in dock, "Mico утащили — окно едет за ним")
    check("self.move(self._stage_pos())" in dock and "def _mico_spot" in dock, "полоска внизу, Mico стоит в левом слоте")
    check("def mouseMoveEvent" in dock and "self._drag_from" in dock, "окно двигается за фон")
    check("return scr.availableGeometry()" in dock, "окно не заходит на панель задач")
    check("self._morph(k, QPoint(spot.x() + px // 2" in dock and "after=self._settled" in dock,
          "Mico плавно переезжает в слот полоски вместе с размером")
    check("self._glide_blob(return_to, 320" in dock, "при выходе Mico возвращается на место")
    iu = read("intel_ui.py")
    check("self._voice_lift_blob" not in iu and "self._voice_drop_blob" not in iu,
          "старая схема «поднять Mico, чтобы влезли кнопки» удалена")


def test_voice_speed_is_applied_to_every_sentence():
    tx = read("voice_text.py")
    check('speed = max(0.5, min(2.0, float(cfg.get("voice_speed", 1.0))))' in tx, "скорость в пределах 0,5–2")
