"""Быстрый чат открывается одной клавишей (по умолчанию F8), сочетания с модификаторами тоже работают."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def test_single_function_key_is_accepted():
    import hotkeys
    assert hotkeys.parse("f8") == (0, 0x77)
    assert hotkeys.parse("F12") == (0, 0x7B)


def test_single_letter_is_still_rejected():
    import hotkeys
    assert hotkeys.parse("a") is None, "буквы без модификатора мешают печатать"
    assert hotkeys.parse("ctrl+alt+m") == (3, 77)


def test_default_chat_key_is_f8_and_old_default_migrates():
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    assert '"hotkey_chat": "f8"' in src
    assert 'cfg.get("hotkey_chat") == "ctrl+alt+m"' in src


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
