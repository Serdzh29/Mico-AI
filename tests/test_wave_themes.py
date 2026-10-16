"""Проверки: готовые наборы цветов волн."""
import os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["APPDATA"] = tempfile.mkdtemp()

import intel


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def test_hour_picks_theme_for_auto():
    check(intel.theme_for_hour(7) == "mint" and intel.theme_for_hour(13) == "ocean", "утро и день")
    check(intel.theme_for_hour(19) == "sunset" and intel.theme_for_hour(2) == "lavender", "вечер и ночь")
    check(intel.theme_colors({"wi_wave_theme": "auto"}, hour=19) == intel.WAVE_THEMES["sunset"][1], "авто — по часу")


def test_named_theme_and_fallback():
    check(intel.theme_colors({"wi_wave_theme": "ocean"}, hour=3) == intel.WAVE_THEMES["ocean"][1], "свой набор")
    check(intel.theme_colors({"wi_wave_theme": "мусор"}, hour=3) == intel.WAVE_THEMES["lavender"][1],
          "неизвестный набор — по времени суток")


def test_theme_source_cycles_smoothly_between_its_colours():
    cfg = {"wi_wave_source": "theme", "wi_wave_theme": "mint"}
    cols = [intel.hex_rgb(c) for c in intel.WAVE_THEMES["mint"][1]]
    check(intel.hex_rgb(intel.wave_base(cfg, "listen", 0.0, hour=12)) == cols[0], "в начале — первый цвет")
    seen = {intel.wave_base(cfg, "listen", k * 0.1, hour=12) for k in range(120)}
    check(len(seen) > 3, "цвет плавно меняется")
    check(intel.wave_base(cfg, "listen", 2 * 3.141592653589793, hour=12) == "#%02X%02X%02X" % cols[1],
          "через цикл — следующий цвет")


def test_other_sources_are_unchanged():
    cfg = {"color": "#112233", "wi_wave_source": "mico"}
    check(intel.wave_base(cfg, "listen", 1.0) == "#112233", "Mico — тот же цвет")
    check(intel.wave_color(dict(cfg, wi_wave_source="theme", wi_wave_theme="sunset"), "listen") ==
          intel.WAVE_THEMES["sunset"][1][0], "набор без фазы — первый его цвет")
    check("theme" in intel.WAVE_SOURCES and "auto" in intel.WAVE_THEMES, "наборы есть в списке")


def test_settings_wire_theme():
    m = read("main.py")
    check("self.wi_theme" in m and "_wi_theme_changed" in m and 'findData("theme")' in m, "выбор набора в настройках")
    check("wi_wave_theme" in m, "набор в DEFAULTS")


def test_wave_paint_uses_palette_cycle():
    check("intel.wave_base(self.cfg, self.state, self.phase)" in read("intel_ui.py"), "полоска идёт по набору")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
