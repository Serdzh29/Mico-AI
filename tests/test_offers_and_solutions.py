"""Предложения Mico с кнопками вариантов; «найди решение» решает сам, без открытия приложений Windows."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import errhelp


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def test_remember_and_last_error():
    errhelp._LAST.update(title="", text="")
    assert errhelp.last_error() is None
    errhelp.remember("Открыть файл", "предупреждение системы безопасности")
    assert errhelp.last_error() == ("Открыть файл", "предупреждение системы безопасности")
    errhelp.remember("пусто", "")                    # пустой текст не перетирает запомненное
    assert errhelp.last_error()[0] == "Открыть файл"


def test_solution_prompt_asks_for_steps_and_forbids_invention():
    p = errhelp.solution_prompt("Ошибка", "нет доступа")
    assert "нет доступа" in p and "шаг" in p and "Ничего не выдумывай" in p


def test_help_app_is_not_opened_anymore():
    assert not hasattr(errhelp, "open_help") and not hasattr(errhelp, "HELP_URI")
    brain = read("brain.py")
    assert "ms-contact-support" not in brain and "open_help" not in brain
    assert "errhelp.solution_prompt" in brain


def test_offers_show_option_buttons():
    w = read("aichat.py")
    assert "def show_offer_row" in w and "def clear_offer_row" in w and "_offer_row = None" in w
    ui = read("intel_ui.py")
    assert "show_offer_row(list(options)" in ui
    assert "Не сейчас" in ui
    assert "_error_options" in ui and "Найти решение" in ui


def test_old_offer_text_removed():
    ui = read("intel_ui.py")
    assert "скажи «покажи журнал»" not in ui and "«найди решение»." not in ui


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
