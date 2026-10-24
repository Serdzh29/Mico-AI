"""Пятый раунд: готовые наборы волн не откатываются, цвет Mico меняет всё сразу, остров сна сверху по центру.
Проверки без Qt: поведение — на чистых функциях, интерфейс — по исходникам."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import intel


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def _src(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


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
    main, ui, wc = _src("main.py"), _src("intel_ui.py"), _src("aichat.py")
    check("def _apply_accent(self):" in main and "self._apply_accent()" in main, "смена цвета — один метод")
    body = main[main.index("def _apply_accent(self):"):main.index("def pick(self):")]
    for part in ("self._style_dialog()", "self._paint_accent_btn()", "self.panel.theme()", "self.panel.intel.restyle()"):
        check(part in body, "в _apply_accent нет: " + part)
    check("def restyle(self):" in ui and "self.aichat._apply_style()" in ui, "чат WI перекрашивается")
    check("class Subtitle" not in ui, "строки над Mico AI больше нет")
    check("def _apply_style(self):" in wc, "чат WI умеет перекраситься")


# ----- мягкий огонёк сна -----
def test_sleep_wiring_in_main_and_blob():
    m, b, ui = _src("main.py"), _src("blob.py"), _src("intel_ui.py")
    check("awake = pyqtSignal()" in b and "self.awake.emit()" in b, "Mico сообщает о любом пробуждении")
    check("blob.slept.connect(lambda: intel_ctl.glow.set_muted(True))" in m, "во сне волны гаснут")
    check("blob.awake.connect(lambda: intel_ctl.glow.set_muted(False))" in m, "проснулся — волны возвращаются")
    check("def set_muted(self, on):" in ui and "goal = 0.0 if self.muted else self.target" in ui,
          "волны плавно гаснут во сне")







if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
    print("test_round5: все проверки прошли")
