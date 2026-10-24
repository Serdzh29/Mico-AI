"""Дизайн-токены: единые скругления и отступы, понятные контрасты."""
import os as _os, sys as _sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_scales_are_monotonic():
    import design
    check(design.RADIUS["s"] < design.RADIUS["m"] < design.RADIUS["l"], "скругления растут")
    vals = list(design.SPACE.values())
    check(vals == sorted(vals), "отступы растут")
    check(all(v % 4 == 0 for v in vals), "отступы кратны 4")
    check(design.MOTION["fast"] < design.MOTION["base"] < design.MOTION["slow"] <= 320, "движение короткое")


def test_settings_use_only_token_radii():
    import re
    src = open(_os.path.join(ROOT, "theme.py"), encoding="utf-8").read()
    a = src.index("def wi_settings_qss(")
    body = src[a:src.index("def windows_accent(")]
    raw = re.findall(r"border-radius:(\d+)px", body)
    check(raw == [], f"в настройках остались скругления без токенов: {raw}")


def test_accent_text_is_readable():
    import design, theme
    for accent in ["#FFCFA3", "#FFB3C6", "#B8C0FF", "#9FD3FF", "#A8E6CF", "#4cc2c4"]:
        for dark in (True, False):
            on = theme.on_accent(accent)
            ratio = design.contrast_ratio(on, accent)
            check(ratio >= design.MIN_CONTRAST, f"{accent} dark={dark}: контраст {ratio:.2f} ниже 4.5")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
