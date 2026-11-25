"""Удаление не мигает терминалами, а кнопки мастера при наведении остаются в цвете Mico."""
import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, "setup", "installer.py"), encoding="utf-8").read()


def test_cleanup_script_runs_in_one_hidden_console():
    assert "_NOWIN | _DETACHED" not in src, "NO_WINDOW вместе с DETACHED открывает окно на каждую команду скрипта"
    body = src[src.index("def _schedule_file_removal"):]
    assert "STARTF_USESHOWWINDOW" in body and "CREATE_NO_WINDOW" in body or "_NOWIN | 0x00000200" in body


def test_hover_color_follows_mico_color():
    body = src[src.index("def _palette"):src.index("def card(")]
    assert 'c["accent_hover"] = _shade(' in body, "цвет наведения должен считаться от цвета Mico"
    m = re.search(r"def _shade.*?return \"#%02x%02x%02x\"", src, re.S)
    assert m


if __name__ == "__main__":
    test_cleanup_script_runs_in_one_hidden_console(); test_hover_color_follows_mico_color(); print("ok")
