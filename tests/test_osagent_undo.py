"""Отмена действий и отказы: что честно обратимо, и что строже подтверждается после отказов."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from win import osagent as O


def test_every_action_states_its_undo_honestly():
    assert set(O.UNDO_NOTE) == set(O.CATALOG), "у каждого действия есть строка про отмену"


def test_inverse_only_where_reversal_is_exact():
    assert O.inverse("set_theme", {"mode": "dark"}) == ("set_theme", {"mode": "light"})
    assert O.inverse("set_theme", {"mode": "light"}) == ("set_theme", {"mode": "dark"})
    assert O.inverse("set_service", {"name": "Spooler", "on": False}) == ("set_service", {"name": "Spooler", "on": True})
    assert O.inverse("set_volume", {"percent": 30}) is None, "прежнее значение не знаем — не обещаем отмену"
    assert O.inverse("close_window", {"title": "Блокнот"}) is None
    assert O.inverse("run_powershell", {"script": "Get-Date"}) is None


def test_rejections_make_open_actions_ask_first():
    assert not O.needs_confirm("open_app"), "обычное открытие — сразу"
    assert not O.needs_confirm("open_app", O.REJECT_LIMIT - 1)
    assert O.needs_confirm("open_app", O.REJECT_LIMIT), "после нескольких отказов спрашиваем заранее"
    assert O.needs_confirm("set_volume"), "изменения всегда с подтверждением"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK osagent undo")
