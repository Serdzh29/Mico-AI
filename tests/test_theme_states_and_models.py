"""Наборы волн меняют цвета всех шести действий; модели для чата и для экрана различаются."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import ast, re
import intel


def _brain_vision():
    """Достаём VISION_MODELS и is_vision_model из brain.py без импорта (там нужны mss и win32gui)."""
    tree = ast.parse(open(_os.path.join(ROOT, "brain.py"), encoding="utf-8").read())
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == "is_vision_model")
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "VISION_MODELS" for t in n.targets))]
    ns = {"re": re}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "brain_vision", "exec"), ns)
    return ns

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


def test_vision_models_detected_by_list_and_name():
    ns = _brain_vision()
    is_v = ns["is_vision_model"]
    for name in ns["VISION_MODELS"]:
        assert is_v(name), name
    assert is_v("llama3.2-vision:11b")
    assert not is_v("qwen2.5:7b")
    assert not is_v("deepseek-r1:8b")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
