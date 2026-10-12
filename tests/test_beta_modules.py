import os as _os, sys as _sys, tempfile, json, zipfile
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import settings_io as S
import report as R
import updates as U
from version import _vt


def _newer(a, b):
    return _vt(a) > _vt(b)

DEFAULTS = {"scale": 1.0, "color": "#FFCFA3", "greet_on_start": True, "retention_days": 30,
            "custom_phrases": [], "loc_consent": None, "city": "", "quiet_mode": False}


def test_export_hides_secrets_and_personal():
    d = tempfile.mkdtemp()
    S.SECRET_KEYS = {"api_token"}                     # проверяем механизм: такой ключ не уходит в файл
    try:
        cfg = dict(DEFAULTS, api_token="SECRET", city="Казань", loc_consent=True, scale=1.5)
        p = _os.path.join(d, "s.json")
        keys = S.export_settings(cfg, p, "33")
        data = json.load(open(p, encoding="utf-8"))
    finally:
        S.SECRET_KEYS = set()
    assert "api_token" not in data and "city" not in data and "loc_consent" not in data
    assert data["scale"] == 1.5 and data["_format"] == "mico-settings"
    assert "scale" in keys


def test_import_applies_known_and_skips_bad():
    d = tempfile.mkdtemp()
    p = _os.path.join(d, "s.json")
    json.dump({"_format": "mico-settings", "scale": 1.2, "color": 5, "unknown_x": 1,
               "api_token": "ключ", "quiet_mode": True}, open(p, "w", encoding="utf-8"))
    cfg = dict(DEFAULTS)
    applied, skipped = S.import_settings(p, cfg, DEFAULTS)
    assert cfg["scale"] == 1.2 and cfg["quiet_mode"] is True
    reasons = dict(skipped)
    assert reasons["color"] == "неверный тип значения"
    assert reasons["unknown_x"].startswith("неизвестная")
    assert reasons["api_token"].startswith("неизвестная")


def test_import_rejects_foreign_file():
    p = _os.path.join(tempfile.mkdtemp(), "x.json")
    json.dump({"a": 1}, open(p, "w", encoding="utf-8"))
    try:
        S.import_settings(p, dict(DEFAULTS), DEFAULTS)
        assert False, "должно было упасть"
    except ValueError:
        pass


def test_report_contains_logs_and_no_secrets():
    app = tempfile.mkdtemp()
    open(_os.path.join(app, "crash.log"), "w").write("трассировка")
    open(_os.path.join(app, "startup.log"), "w").write("этапы")
    out = tempfile.mkdtemp()
    path, included = R.build_report(app, out, "33", dict(DEFAULTS, city="Казань"), 26200)
    assert set(included) == {"crash.log", "startup.log"}
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        assert {"README.txt", "info.json", "settings.json", "crash.log", "startup.log"} <= names
        blob = " ".join(z.read(n).decode("utf-8", "replace") for n in names)
        assert "SECRET" not in blob and "Казань" not in blob
        assert "history" not in " ".join(names) and "index" not in " ".join(names)


def test_update_parse_and_compare():
    info = U.parse('{"version": "34", "url": "https://example.org/Mico.exe", "notes": "новое"}')
    assert info["version"] == "34" and _newer(info["version"], "33")
    assert not _newer("33", "33") and not _newer("32", "33")
    assert _newer("34", "3.29") is True
    try:
        U.parse('{"url": "x"}')
        assert False
    except ValueError:
        pass


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
