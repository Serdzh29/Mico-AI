"""Пятый раунд: голос кнопкой 🎤 через выбранный движок (Vosk или Windows), путь к модели Vosk с не-латинскими
буквами, готовые наборы волн не откатываются, цвет Mico меняет всё сразу, остров сна сверху по центру.
Проверки без Qt: поведение — на чистых функциях, интерфейс — по исходникам."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import intel
import voice as V


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def _src(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


# ----- голос -----
def test_vosk_path_keeps_ascii_and_is_identity_off_windows():
    check(V.vosk_path("C:\\Mico\\models\\vosk") == "C:\\Mico\\models\\vosk", "ASCII-путь не меняется")
    cyr = "C:\\Users\\Иван\\AppData\\Mico\\model"
    check(V.vosk_path(cyr) == cyr, "не на Windows путь возвращается как есть")
    check(V.vosk_path("") == "", "пустой путь — пустой")


def test_vosk_problem_explains_what_is_missing():
    p = V.vosk_problem("")
    check(p and ("пакеты" in p or "модель" in p), "без модели и пакетов — понятная причина: " + p)
    err = V.listen_vosk("", 2)
    check(err[0] == "" and err[1], "Vosk без модели не падает, а объясняет")


def test_mic_button_paths_are_engine_aware():
    main = _src("main.py")
    wc = _src("wichat.py")
    check("text, err = voice.listen_once(self.cfg, 8)" in main, "кнопка 🎤 в чате — через выбранный движок")
    check("text, err = voice.listen_once(self.cfg, 8)" in wc, "кнопка 🎤 в чате WI — через выбранный движок")
    check("voice.listen(8)" not in main and "voice.listen(8)" not in wc, "прямого вызова Windows больше нет")
    check("Голос не запустился:" in main, "ошибка запуска голоса показывается, а не глотается")


# ----- волны: готовый набор не откатывается -----
def test_theme_waves_keep_their_color_in_every_state():
    cfg = {"wi_wave_source": "theme", "wi_wave_theme": "ocean", "color": "#FFCFA3"}
    allowed = {c.upper() for c in intel.WAVE_THEMES["ocean"][1]}
    for state in ("listen", "think", "warn"):
        for step in range(40):
            hexc = intel.wave_base(cfg, state, step * 0.31, hour=12)
            r, g, b = intel.hex_rgb(hexc)
            check(0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255, "цвет в пределах")
            # цвет всегда внутри набора (с учётом плавного перехода между его цветами)
            cols = [intel.hex_rgb(c) for c in allowed]
            lo = [min(c[i] for c in cols) for i in range(3)]
            hi = [max(c[i] for c in cols) for i in range(3)]
            check(all(lo[i] - 1 <= (r, g, b)[i] <= hi[i] + 1 for i in range(3)),
                  f"цвет вне набора: {hexc}")


def test_wave_color_from_mico_follows_the_setting():
    cfg = {"wi_wave_source": "mico", "color": "#7FB8FF"}
    check(intel.wave_color(cfg, "think") == "#7FB8FF", "волны берут цвет Mico, а не цвет действия")
    cfg["color"] = "#D6B8FF"
    check(intel.wave_color(cfg, "listen") == "#D6B8FF", "смена цвета Mico сразу меняет волны")


# ----- цвет Mico меняет всё -----
def test_accent_change_restyles_every_window():
    main, ui, wc = _src("main.py"), _src("intel_ui.py"), _src("wichat.py")
    check("def _apply_accent(self):" in main and "self._apply_accent()" in main, "смена цвета — один метод")
    body = main[main.index("def _apply_accent(self):"):main.index("def pick(self):")]
    for part in ("self._style_dialog()", "self._paint_accent_btn()", "self.panel.theme()", "self.panel.intel.restyle()"):
        check(part in body, "в _apply_accent нет: " + part)
    check("def restyle(self):" in ui and "self.sub._apply_style()" in ui and "self.wichat._apply_style()" in ui,
          "строка и чат WI перекрашиваются")
    check("def _apply_style(self):" in ui.split("class Subtitle")[1].split("class _Bridge")[0],
          "стиль строки вынесен в метод, его можно вызвать снова")
    check("def _apply_style(self):" in wc, "чат WI умеет перекраситься")


# ----- остров сна -----
def test_sleep_island_is_black_pill_at_top_center():
    s = _src("sleep_island.py")
    check("class SleepIsland" in s and "wake = pyqtSignal()" in s, "островок и сигнал пробуждения")
    check("def _pill(self, screen):" in s and "g.center().x() - self.W // 2" in s and "g.top() + self.TOP" in s,
          "пилюля сверху по центру экрана")
    check("p.setBrush(QColor(0, 0, 0))" in s, "островок чёрный")
    check("def _mico_spot" in s and "QPropertyAnimation" in s and 'b"geometry"' in s,
          "островок вырастает из Mico и втягивается обратно")
    check("def retract_to(self, blob):" in s and "self.hide_island" in s, "при пробуждении втягивается и прячется")
    check("mousePressEvent" in s and "self.wake.emit()" in s, "тап будит")
    check("def _draw_sleeper(self, p):" in s and "closed" not in s.lower() and "p.drawArc" in s,
          "внутри острова — спящий Mico с закрытыми глазами-дугами")


def test_sleep_wiring_in_main_and_blob():
    m, b, ui = _src("main.py"), _src("blob.py"), _src("intel_ui.py")
    check("awake = pyqtSignal()" in b and "self.awake.emit()" in b, "Mico сообщает о любом пробуждении")
    check("blob.awake.connect(lambda: sleep_isl.retract_to(blob))" in m, "островок втягивается при пробуждении")
    check("blob.slept.connect(lambda: intel_ctl.glow.set_muted(True))" in m, "во сне волны гаснут")
    check("blob.awake.connect(lambda: intel_ctl.glow.set_muted(False))" in m, "проснулся — волны возвращаются")
    check("def set_muted(self, on):" in ui and "goal = 0.0 if self.muted else self.target" in ui,
          "волны плавно гаснут во сне")

# ----- пробуждение голосом -----
def test_vosk_wake_detector_fires_once_per_word():
    class FakeRec:
        def __init__(self, partials):
            self.partials, self.resets = list(partials), 0
        def AcceptWaveform(self, data):
            return False
        def PartialResult(self):
            return '{"partial": "%s"}' % (self.partials.pop(0) if self.partials else "")
        def Reset(self):
            self.resets += 1
    rec = FakeRec(["", "мико", "мико"])
    words = ["мико", "мыко"]
    hits = [V.VoskListener._wake_heard(rec, b"x", words) for _ in range(3)]
    check(hits == [False, True, True], str(hits))
    check(rec.resets == 2, "после пробуждения распознаватель сбрасывается")


def test_wake_word_threshold_is_lower_than_phrase_threshold():
    check(V.WAKE_MIN_CONFIDENCE < V.MIN_CONFIDENCE, "одно слово «Мико» принимаем увереннее, чем фразу")
    check(V.wake_words_list(("мико,", "мико", "miko")) == ["мико", "miko"], "слова без знаков и повторов")


def test_sleeping_mico_is_woken_by_voice_and_chat_waits_for_landing():
    m, b = _src("main.py"), _src("blob.py")
    check("wake_requested = pyqtSignal()" in m and "panel.wake_requested.connect(lambda: sleep_isl.wake.emit())" in m,
          "голосовое «Мико» будит спящего тем же путём, что тап по острову")
    check("if self.blob.asleep and not wake:" in m, "спящий слушает только слово «Мико»")
    check("blob.woke.connect(lambda: QTimer.singleShot(blob.WAKE_SETTLE_MS, panel.show_near))" in m,
          "чат открывается после приземления Mico, а не налезает на него")
    check("WAKE_SETTLE_MS = 650" in b, "пауза после пробуждения задана в blob")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
    print("test_round5: все проверки прошли")
