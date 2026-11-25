"""Наборы волн меняют цвета всех шести действий; vision-модели убраны — экран смотрит Groq."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import ast, re
from assist import intel


def _brain_vision():
    """Читаем brain.py без импорта (там нужны mss и win32gui)."""
    return open(_os.path.join(ROOT, "core/brain.py"), encoding="utf-8").read()

STATES = {"listen", "think", "break", "watch", "tip", "warn"}


def test_every_preset_has_six_distinct_state_colors():
    for key, (name, cols, states) in intel.WAVE_THEMES.items():
        if states is None:
            assert key == "auto", key
            continue
        assert set(states) == STATES, (key, set(states))
        assert len(set(v.upper() for v in states.values())) == 6, key
        assert all(intel._HEX.fullmatch(v) for v in states.values()), key


def test_preset_changes_state_colors_and_auto_uses_defaults():
    assert intel.theme_states("ocean") != intel.theme_states("sunset")
    assert intel.theme_states("ocean")["listen"] == "#9FD3FF"
    assert intel.theme_states("auto") == intel.DEFAULT_COLORS
    assert intel.theme_states("мусор") == intel.DEFAULT_COLORS


def test_preset_colors_pass_state_colors_check():
    for key in ("sunset", "ocean", "mint", "lavender"):
        cfg = {"wi_colors": intel.theme_states(key)}
        assert intel.state_colors(cfg) == {k: v.upper() for k, v in intel.theme_states(key).items()}, key


def test_vision_models_are_gone_from_the_code():
    brain = _brain_vision()
    assert "VISION_MODELS" not in brain and "is_vision_model" not in brain, "выбор vision-моделей убран"
    main = open(_os.path.join(ROOT, "mico.py"), encoding="utf-8").read()
    assert 'cfg.pop("vision_model", None)' in main, "старый выбор vision-модели очищается при загрузке"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
