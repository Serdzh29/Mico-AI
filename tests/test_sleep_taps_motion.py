"""Mico: сон (растворяется на месте, будит только нажатие на знак сна, курсор не будит, полоски во сне пропадают),
знак сна — месяц с буквами z, наклон головы ограничен, без случайного смешка, нажатия в голосовом режиме.
Проверяется по исходникам, как остальные тесты анимаций (без Qt)."""
import os as _os
import re
import sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def block(src, start, length=900):
    i = src.index(start)
    return src[i:i + length]


def test_head_tilt_is_limited_and_smoothed_by_time():
    b = read("blob.py")
    check(re.search(r"HEAD_TILT_MAX = [\d.]+", b) is not None, "есть общий лимит наклона головы")
    check("p.rotate(head + shake + spin_turn)" in b and "head = max(-HEAD_TILT_MAX, min(HEAD_TILT_MAX, self.tilt + sway))" in b,
          "в отрисовке голова не наклоняется дальше лимита")
    check("tilt_goal = TILT.get" in b and "max(-HEAD_TILT_MAX, min(HEAD_TILT_MAX, tilt_goal))" in b,
          "цель наклона тоже ограничена")
    check("math.exp(-dt * 7)" in b and "math.exp(-dt * 9)" in b, "наклон сглажен по времени кадра, а не по числу кадров")
    check("sway += self._tilt_dir * 6 * math.sin" in b, "поклон головы при простое мягче (6° вместо 14°)")
    check("random.uniform(-6, 6)" in b and "random.uniform(0.09, 0.2)" in b, "рот меняется мягче, без резких поворотов")


def test_no_random_chuckle_in_idle_or_talk():
    b = read("blob.py")
    check('random.choice(["lookaround", "blink2", "wink", "headtilt"])' in b, "простой без смешка")
    check('random.choice(["headtilt", "blink2"])' in b, "во время разговора без смешка")
    check('random.choice(["cheer"' not in b and '"cheer", "headtilt"' not in b, "смешок случайно не запускается")


def test_sleep_moves_down_shrinks_and_wakes_by_clicking_mico():
    b = read("blob.py")
    sn = block(b, "    def sleep_now(self):", 500)
    check("self.vanish()" not in sn and "self.locked = True" not in sn, "Mico не растворяется, а едет")
    check("sleepmode.home_corner(self.asleep" in b, "во сне Mico едет к своему месту")
    check("if self.asleep:                                     # во сне дыхание медленное" in b
          or "if self.asleep:" in b, "во сне есть покачивание")
    tick = block(b, "        cur = QCursor.pos()", 260)
    check("if not self.asleep:" in tick and "self.last_input = now" in tick, "курсор не трогает спящего")
    rel = block(b, "    def mouseReleaseEvent(self, e):", 400)
    check("if self.asleep:" in rel and "self.wake(" in rel, "нажатие по Mico будит его")
    main = read("main.py")
    check("sleep_glow" not in main, "знака сна (месяца) больше нет")


def test_sleep_shows_z_letters_above_head():
    b = read("blob.py")
    s = block(b, 'elif mood == "sleepy":                              # сон', 700)
    check('"z"' in s and "math.sin(math.pi * ph)" in s, "буквы z плывут вверх и гаснут")
    check("cy - R * (1.0 + 0.9 * ph)" in s, "буквы над головой")


def test_strips_disappear_completely_during_sleep():
    ui = read("intel_ui.py")
    tick = block(ui, "    def _tick(self):\n        now = time.time()\n        dt = min(0.1", 700)
    check("if self.muted and self.level < 0.02:" in tick and "self.hide()" in tick, "во сне полоски полностью пропадают")


def test_voice_mode_taps_are_playful_and_warn_when_too_fast():
    b = read("blob.py")
    check("tapped = pyqtSignal()" in b and "self.tapped.emit()" in b, "каждое нажатие считается")
    dbl = block(b, "    def mouseDoubleClickEvent(self, e):", 500)
    check("self.tapped.emit()" in dbl and "if not self.voice_taps:" in dbl,
          "двойной щелчок в голосовом режиме — нажатие, а не настройки")
    ui = read("intel_ui.py")
    body = block(ui, "    def _blob_tapped(self):", 900)
    check("if not self.voice_mode or self.voice_dock.in_pill():" in body, "вне голосового режима и в обводке не реагируем")
    check('self.blob.set_mood("excited", 2.5)' in body, "веселая эмоция на нажатие")
    check("intel.TAP_LIMIT" in body and "self.voice.speak(intel.TAP_WARNING" in body, "часто нажимают — просим не спешить")
    check("self.voice_dock.show_mico(intel.TAP_WARNING)" in body, "просьба идёт в субтитры: чат в голосовом режиме закрыт")
    check("self.blob.tapped.connect(self._blob_tapped)" in ui, "нажатия подключены")
    main = read("main.py")
    i = main.index("def _blob_clicked():")
    check("intel_ctl.voice_mode" in main[i:i + 300] and "return" in main[i:i + 300],
          "одиночный клик в голосовом режиме чат не открывает")
    check("blob.settings_requested.connect(lambda: None if (intel_ctl is not None and intel_ctl.voice_mode)" in main,
          "двойной щелчок в голосовом режиме не открывает настройки")
    intel_src = read("intel.py")
    check("TAP_WARNING = " in intel_src and "TAP_WINDOW_SEC" in intel_src, "фраза и окно нажатий вынесены в intel")
