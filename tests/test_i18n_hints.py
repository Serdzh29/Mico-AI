"""Второй этап перевода: все описания настроек переведены и выводятся на английском."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import i18n, i18n_hints, settings_info as si


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def test_every_description_has_english():
    texts = set(si.INFO.values()) | set(si.CFG_HINTS.values())
    missing = sorted(t for t in texts if t not in i18n_hints.EN_HINTS)
    assert not missing, missing[:5]


def test_no_stale_translations():
    texts = set(si.INFO.values()) | set(si.CFG_HINTS.values())
    stale = sorted(k for k in i18n_hints.EN_HINTS if k not in texts)
    assert not stale, stale[:5]


def test_english_values_are_real_text():
    assert all(len(v.split()) >= 2 for v in i18n_hints.EN_HINTS.values())


def test_descriptions_switch_language():
    key = next(iter(si.INFO))
    i18n.set_language("en")
    try:
        assert i18n.t(si.INFO[key]) == i18n_hints.EN_HINTS[si.INFO[key]]
    finally:
        i18n.set_language("ru")
    assert i18n.t(si.INFO[key]) == si.INFO[key]


def test_settings_window_and_describe_command_use_translations():
    main, cmds = read("main.py"), read("commands.py")
    assert "hint = i18n.t(raw_hint) if raw_hint else None" in main
    assert 'text = i18n.t(settings_info.info_for(name) or "Описания пока нет.")' in cmds


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
