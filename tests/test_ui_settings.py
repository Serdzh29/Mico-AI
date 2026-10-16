"""Окно настроек и ряд кнопок: проверки без Qt (Qt на машине сборки может не быть).
Что нельзя проверить здесь — внешний вид; для него нужен запуск на Windows (см. BETA_CHECKLIST)."""
import os as _os, re, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import chips
import settings_info as SI
import theme

MAIN = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def test_zero_chips_hides_everything_in_both_modes():
    check(chips.pick({"chips_count": 0}) == [], "0 кнопок — ничего не показываем")
    check(chips.pick({"chips_count": 0, "chips_mode": "manual", "chips_pinned": [chips.CATALOG[0].id]}) == [],
          "в ручном режиме 0 тоже убирает ряд")
    check(len(chips.pick({"chips_count": 1})) == 1, "1 кнопка — как раньше")

def test_every_setting_row_has_a_hint():
    keys = set(re.findall(r'self\._row\(f, [^,]+, [^,]+, "(\w+)"\)', MAIN))
    keys |= set(re.findall(r'self\._block\(self\.\w+, "(\w+)"\)', MAIN))
    block = MAIN[MAIN.index("NAME2KEY = {"):MAIN.index("def _block")]
    keys |= set(re.findall(r':\s*"(\w+)"', block))          # значения: ключи настроек, а не названия
    keys |= {"color", "scale", "opacity", "chat_scale", "theme", "settings_size", "placement", "search_url",
             "retention_days", "sleep_after_min", "sleep_corner", "update_check", "menu_max", "hotkey_chat",
             "city", "proactive_break_min", "initiative_min", "chips_mode", "chips_count",
             "chips_hide_on_send", "text_model", "vision_model"}
    missing = sorted(k for k in keys if k not in SI.CFG_HINTS)
    check(not missing, f"нет подсказки для: {missing}")

def test_reset_button_style_is_pale_red_with_black_text():
    check("#f3c9c4" in theme.RESET_QSS and "color:#000000" in theme.RESET_QSS, "бледно-красный фон, чёрный текст")

def test_one_font_family_for_the_whole_app():
    check(theme.FONT_FAMILY == "Inter", "главный шрифт — Inter")
    check("theme.load_fonts()" in MAIN and "app.setFont(theme.app_font())" in MAIN, "шрифт грузится и задаётся приложению")
    check("app.setStyleSheet(theme.FONT_QSS)" in MAIN, "шрифт задан и в стилях")

def test_wheel_does_not_change_sliders_or_spinboxes():
    for cls in ("NoWheelSlider", "NoWheelSpinBox", "NoWheelComboBox"):
        check(f"class {cls}(" in MAIN, cls)
    check(MAIN.count("        e.ignore()") >= 3, "колесо передаётся окну, а не меняет значение")

def test_tabs_renamed_and_commands_first():
    check('"Функции")' in MAIN, "вкладка переименована")
    check('"Возможности")' not in MAIN, "старое название убрано")
    i = MAIN.index('tabs.addTab(page((ph, "Свои фразы")')
    check(i > 0, "команды (свои фразы и кнопки) идут первыми")

def test_version_and_about_are_on_their_own_row_above_buttons():
    check('"О программе"' in MAIN and "class AboutDialog" in MAIN, "кнопка «О программе» и окно")
    check("top.addWidget(ver)" in MAIN and "root.addWidget(bb)" in MAIN, "версия и «О программе» — отдельным рядом")
    check("bottom.addWidget" not in MAIN, "кнопки не делят строку с версией (иначе обрезаются)")

def test_chat_chips_row_can_hide_after_send():
    check("chips_hide_on_send" in MAIN and "self.chips_box.setVisible" in MAIN, "ряд можно скрыть")
    check("def _on_input_focus" in MAIN, "вернуть ряд, когда нажмут в поле ввода")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
