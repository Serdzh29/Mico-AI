"""Голосовая полоска, раунд 15: время убрано, вынутый Mico — полоска только из кнопок, тап без прыжка,
сон в обводке, микрофон выключен — Mico не засыпает. Проверяется по исходникам (без Qt и микрофона)."""
import os as _os
import sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def block(src, start, size):
    i = src.index(start)
    return src[i:i + size]


def check(cond, what):
    assert cond, what


def test_timer_is_removed_from_voice_bar():
    vd = read("voice_dock.py")
    for gone in ("time_lbl", "_tick_clock", "TIME_H", "SLOT_BOTTOM", "_place_time", "vtime"):
        check(gone not in vd, f"таймер разговора убран: {gone}")


def test_controls_mode_keeps_only_buttons():
    vd = read("voice_dock.py")
    body = block(vd, "    def _mode_visibility(self, mode):", 800)
    check('self.slot.setVisible(mode != "controls")' in body, "вынут — слота с Mico нет")
    check('btn.setVisible(mode != "mico")' in body, "кнопки видны, кроме режима обводки")
    check('self.slot.setFixedWidth(BLOB_PX if mode == "mico" else SLOT_W)' in body, "в режиме сна слот — ровно под Mico")


def test_tap_does_not_jump():
    iu = read("intel_ui.py")
    body = block(iu, "    def _blob_tapped(self):", 1400)
    normal = body[body.index('set_mood("excited", 2.5)'):]
    check("jump(" not in normal, "обычный тап без прыжка: Mico не съезжает")
    check("self.voice_dock.toggle_detach()" in normal, "тап вынимает/возвращает Mico")


def test_pill_sleep_and_wake():
    vd = read("voice_dock.py")
    iu = read("intel_ui.py")
    check("def sleep_pill(self):" in vd and "def expand_pill(self):" in vd, "есть сон и разворот обводки")
    check("self.blob.rest_pos = spot" in block(iu, "    def _voice_slept(self):", 500),
          "при пробуждении Mico не прыгает на старое место")
    check("self.voice_dock.expand_pill()" in block(iu, "    def _voice_woke(self):", 300), "нажатие будит и разворачивает")
    check("self.voice_dock.expand_pill()" in block(iu, "    def _on_wake(self, rest):", 400), "«мико» будит и разворачивает")
    expand = block(vd, "    def expand_pill(self):", 400)
    check("self._blob.locked = True" in expand, "после пробуждения Mico снова закреплён в полоске")


def test_mic_off_keeps_mico_visible():
    iu = read("intel_ui.py")
    check("self.blob.keep_awake = on" in block(iu, "    def _voice_mute_toggle(self):", 400),
          "микрофон выключен — Mico не засыпает")


def test_mico_stays_locked_in_voice_mode():
    vd = read("voice_dock.py")
    check("blob.keep_awake = False" in vd, "в полоске Mico может уснуть (не keep_awake)")
    check("b.locked = True" in block(vd, "    def sleep_pill(self):", 600),
          "в обводке Mico закреплён: не уезжает в угол сна")


def test_detach_and_return_morph_around_center():
    vd = read("voice_dock.py")
    bl = read("blob.py")
    check("def _morph(self, k_to, center_to, after=None, ms=640):" in vd, "переезд плавный, одновременно с размером")
    check("b.morphing = True" in vd and "b.morphing = False" in vd, "на время переезда размер меняется вокруг центра")
    check("if self.morphing:" in bl and "cx, cy = self.x() + self.width() // 2" in bl,
          "blob держит центр при изменении размера")
    check("self._set_mode(\"controls\", follow=False)" in block(vd, "    def toggle_detach(self):", 900),
          "вынутый Mico: полоска сужается до кнопок")
    check("self._morph(k1, center" in vd, "переходы идут через _morph")


def test_mico_centered_on_bar_height():
    vd = read("voice_dock.py")
    body = block(vd, "    def _mico_spot(self, x=None, size=None):", 500)
    check("int(BAR_H / 2 - BODY_CY * h)" in body, "тело Mico по центру полоски, а не выше")


def test_waves_removed_subtitles_in_caption_box():
    vd = read("voice_dock.py")
    check("class WaveBars" not in vd, "волны удалены")
    body = block(vd, "    def _show_mid(self):", 500)
    check("self.caption.show()" in body and "self.caption.hide()" in body, "субтитры — отдельная плашка")
    check("self._mode == \"full\"" in body, "субтитры не показываем в режиме сна")
    check("self.caption.move(x, max(0, y))" in vd and "CAPTION_GAP" in vd, "плашка над полоской, а не внутри")


def test_glow_is_even_and_thin():
    vd = read("voice_dock.py")
    body = block(vd, "    def paintEvent(self, _):", 900)
    check("steps = 6" in body and "c.setAlpha(int(64" in body, "ровный тонкий ореол без лучей")
    check("paint_glow" not in vd, "старое свечение с 14 контурами убрано")


def test_detached_mico_floats_above_bar():
    vd = read("voice_dock.py")
    body = block(vd, "    def _detach_spot(self, px):", 500)
    check("self.y() + GLOW - DETACH_GAP - px" in body, "вынутый Mico висит над полоской, а не в центре экрана")
    check("self._detach_spot(px1)" in block(vd, "    def _set_mode(self, mode", 900), "переход вынутого Mico — к точке над полоской")


def test_sleep_island_fits_mico():
    vd = read("voice_dock.py")
    body = block(vd, "    def _mode_visibility(self, mode):", 800)
    check("self.row_lay.setContentsMargins(SLOT_X, 0, SLOT_X if mode == \"mico\" else END_PAD, 0)" in body,
          "в режиме сна отступы симметричны — Mico по центру обводки")
    check("b.set_mood(\"sleepy\")" in block(vd, "    def sleep_pill(self):", 800), "во сне Mico спит")
    iu = read("intel_ui.py")
    check("if on and not self.blob.asleep:" in block(iu, "    def _voice_listening(self, on):", 300),
          "во сне настроение не сбивается на «любопытный»")


def test_question_during_sleep_wakes_and_listens():
    iu = read("intel_ui.py")
    check("self.voice.begin_listening()" in block(iu, "    def _voice_slept(self):", 500),
          "во сне вопросы слушаем")
    check("self.voice_dock.expand_pill()" in block(iu, "    def _on_voice_said(self, text):", 900),
          "вопрос во сне будит Mico и разворачивает полоску")


def test_no_text_chat_on_start_in_intelligence_mode():
    m = read("main.py")
    body = block(m, "    def open_chat_on_start():", 600)
    check("if intel_ctl.on():\n            return" in body, "в режиме Intelligence текстовый чат при запуске не открываем")
    check("panel.show_near(activate=False)" in body, "в обычном режиме чат по-прежнему открывается")


def test_new_transition_stops_the_previous_one():
    vd = read("voice_dock.py")
    body = block(vd, "    def _morph(self, k_to, center_to, after=None, ms=640):", 900)
    check("self._morph_anim.stop()" in body, "новый переезд останавливает прежний, а не спорит с ним")
    check("self._morph_anim = None" in block(vd, "    def _stop_anims(self):", 400), "остановка сбрасывает ссылку")
    check("self._blob.morphing = False" in block(vd, "    def _stop_anims(self):", 500),
          "прерванный переезд не оставляет Mico в режиме «вокруг центра»")


def test_no_empty_gap_when_detached():
    vd = read("voice_dock.py")
    check("self.spacer.setVisible(mode == \"full\")" in block(vd, "    def _mode_visibility(self, mode):", 800),
          "распорка есть только в полной полоске — без пустоты в режиме «только кнопки»")
    check("return 2 * GLOW + SLOT_X + END_PAD + 5 * BTN" in vd, "ширина «только кнопки» точная")
    check("anim.finished.connect(lambda: self._snap_width(target, cx))" in block(vd, "    def _set_mode(self, mode", 1800),
          "в конце перехода ширина выставляется точно")


def test_buttons_do_not_lift_the_bar():
    vd = read("voice_dock.py")
    check("def _lift(self" not in vd and "POP_LIFT" not in vd, "подъёма полоски нет: кнопки не двигают бар")
    check("self._lift(" not in vd, "ни панели, ни субтитры не поднимают полоску")


def test_mico_stays_visible_after_any_button():
    vd = read("voice_dock.py")
    body = block(vd, "    def _after_click(self, slot):", 500)
    check("self._blob.raise_()" in body and "self._blob.show()" in body, "после нажатия Mico снова на виду")
    check("self._after_click(slot)" in block(vd, "    def _button(self, row, tip, slot):", 900), "кнопки идут через _after_click")
    check("self._after_click(slot)" in block(vd, "    def _chip(self, text, slot):", 400), "чипы идут через _after_click")


def test_full_width_is_formula_so_return_does_not_shift():
    vd = read("voice_dock.py")
    check("def _full_w(self):" in vd and "return 2 * GLOW + SLOT_X + SLOT_W + 5 * BTN" in vd,
          "полная ширина по формуле: возврат Mico не смещается")
    check('if mode == "full":\n            return self._full_w()' in vd, "полная полоска берёт ширину из формулы")


def test_buttons_and_chips_are_rounded():
    vd = read("voice_dock.py")
    check('b.setStyleSheet(f"QPushButton {{ border-radius:{BTN // 2}px; }}")' in vd, "круглые кнопки полоски")
    check('b.setStyleSheet("QPushButton { border-radius:16px; }")' in vd, "скруглённые чипы")


def test_all_settings_opens_mico_ai_settings():
    vd = read("voice_dock.py")
    main = read("main.py")
    check("Все настройки Mico AI" in vd and "all_settings = pyqtSignal()" in vd, "пункт «Все настройки Mico AI» есть")
    check("intel_ctl.voice_dock.all_settings.connect(open_settings)" in main, "пункт открывает настройки Mico AI")


def test_subtitle_button_shows_something_at_once():
    vd = read("voice_dock.py")
    body = block(vd, "    def _show_mid(self):", 600)
    check("Субтитры включены" in body, "после нажатия видна подсказка, даже до первой речи")


def test_caption_helper_is_static_so_panel_build_does_not_crash():
    vd = read("voice_dock.py")
    check("    @staticmethod\n    def _caption(text):" in vd,
          "_caption без self: вызывается как self._caption(текст) при сборке панелей")
