import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
from core import uilayout as U


def test_old_config_with_window_mode_gets_panel_once():
    cfg = {"panel_side": False}                          # так сохраняли старые версии
    assert U.migrate(cfg) is True
    assert cfg["panel_side"] is True and cfg["ui_layout"] == U.LAYOUT_VERSION


def test_user_choice_survives_after_migration():
    cfg = {"panel_side": True, "ui_layout": U.LAYOUT_VERSION}
    cfg["panel_side"] = False                            # пользователь выбрал «окно рядом» в настройках
    assert U.migrate(cfg) is False
    assert cfg["panel_side"] is False


def test_new_config_without_key_is_migrated_to_panel():
    cfg = {}                                             # файла не было — дефолт и так панель
    assert U.migrate(cfg) is True
    assert cfg["panel_side"] is True


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
