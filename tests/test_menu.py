import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import menu_items as M


def test_defaults_are_few_and_end_with_exit():
    v = M.visible({})
    assert v[-1] == "exit" and len(v) <= M.DEFAULT_MAX
    assert set(v) <= set(M.DEFAULT_ON)


def test_limit_is_respected_and_exit_always_present():
    v = M.visible({"menu_items": list(M.LABELS), "menu_max": 3})
    assert len(v) == 3 and v[-1] == "exit"
    assert M.visible({"menu_items": ["settings"], "menu_max": 3}) == ["settings", "exit"]


def test_unknown_items_and_order():
    v = M.visible({"menu_items": ["nope", "quiet", "settings"], "menu_max": 10})
    assert "nope" not in v and v.index("settings") < v.index("quiet") and v[-1] == "exit"


def test_chat_item_is_gone_from_menu():
    assert "chat" not in M.LABELS and "chat" not in M.DEFAULT_ON
    assert "chat" not in M.visible({"menu_items": ["chat", "settings"], "menu_max": 10})


def test_every_item_has_label_and_group():
    for item, label, group in M.ITEMS:
        assert label and group and item in M.LABELS


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
