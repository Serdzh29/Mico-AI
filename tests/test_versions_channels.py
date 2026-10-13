import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import version as V
import features as F
from version import _vt


def is_newer(a, b):
    return _vt(a) > _vt(b)


def test_date_versions_order_correctly():
    order = ["29", "38", "2026.10.12", "2026.10.1201", "2026.10.1202", "2026.10.13", "2026.11.01", "2027.01.01"]
    keys = [V._vt(x) for x in order]
    assert keys == sorted(keys)
    assert is_newer("2026.10.1201", "2026.10.12") and not is_newer("2026.10.12", "2026.10.12")
    assert is_newer("2026.10.12", "38") and is_newer("2026.10.13", "2026.10.1202")


def test_old_numbers_still_understood():
    assert V._label("3.29") == "29" and V._label("2026.10.1201") == "2026.10.1201"
    assert V.whats_new("3.29").startswith("🆕 Mico обновился: 29 →")


def test_day_suffix_is_unambiguous():
    assert V._vt("2026.10.01") == (2026, 10, 1, 0)
    assert V._vt("2026.10.0102") == (2026, 10, 1, 2)


def test_beta_features_only_in_beta_channel():
    import version
    saved, version.BUILD_CHANNEL = version.BUILD_CHANNEL, "beta"     # проверяем поведение бета-сборки
    try:
        assert F.enabled("planner", {"update_channel": "beta"})
        assert not F.enabled("planner", {"update_channel": "stable"})
        assert F.enabled("memory", {"update_channel": "stable"})
    finally:
        version.BUILD_CHANNEL = saved
    assert "BETA" not in F.explain("memory") if "memory" in F.FEATURES else True
    assert F.DEV_NOTE in F.explain("initiative")


def test_setting_features_have_beta_flag():
    for key, feat in F.SETTING_FEATURE.items():
        assert feat in F.FEATURES, (key, feat)


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
