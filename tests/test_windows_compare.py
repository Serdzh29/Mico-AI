import os as _os, sys as _sys, datetime
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import windows_compare as WC

D = WC.load()
TODAY = datetime.date(2026, 10, 12)
PRO = {"edition": "Professional"}
HOME = {"edition": "Core"}


def test_unsupported_version_is_refused_not_compared():
    text = WC.answer_compare("сравни 21h2 и 22h2", HOME, D, TODAY)
    assert "не поддерживается" in text and "10 октября 2023" in text
    assert "→" not in text


def test_windows10_is_refused():
    assert "только Windows 11" in WC.answer_compare("сравни windows 10 и 11", HOME, D, TODAY)
    assert "Windows 10" in WC.current({"build": 19045, "ubr": 5000, "edition": "Professional"}, D, TODAY)


def test_compare_stable_versions_lists_highlights_and_sources():
    text = WC.answer_compare("сравни 25h2 и 26h2", PRO, D, TODAY)
    assert "26300.9457" in text and "Резервное копирование параметров" in text
    assert "Источники:" in text


def test_insider_build_to_release_shows_only_newer_changes():
    text = WC.compare("26300.8697", "26300.9457", D, "home_pro", TODAY)
    assert "26300.8697 → 26300.9457" in text
    assert "26300.8758" in text and "панели задач" in text
    assert "Резервное копирование" in text


def test_insider_build_of_unsupported_version_is_refused():
    d = dict(D, lifecycle=[r for r in D["lifecycle"] if r["version"] != "26H2"])
    assert "нет в моих данных о поддержке" in WC.compare("26300.8697", "26300.9457", d, "home_pro", TODAY)


def test_support_depends_on_edition():
    # 23H2: Home и Pro кончилась 11 ноября 2025, Enterprise идёт до 10 ноября 2026
    assert "не поддерживается" in WC.current({"build": 22631, "ubr": 6000, "edition": "Core"}, D, TODAY)
    text = WC.current({"build": 22631, "ubr": 6000, "edition": "Enterprise"}, D, TODAY)
    assert "10 ноября 2026" in text and "осталось 29 дн" in text
    assert "дн.." not in text


def test_home_24h2_says_support_ends_tomorrow():
    text = WC.current({"build": 26100, "ubr": 7000, "edition": "Core"}, D, TODAY)
    assert "заканчивается завтра" in text and "13 октября 2026" in text


def test_current_build_compares_with_previous_known():
    text = WC.current({"build": 26300, "ubr": 9457, "edition": "Professional"}, D, TODAY)
    assert "Сейчас у тебя Windows 11 26H2, сборка 26300.9457" in text
    assert "26300.9278 → 26300.9457" in text and "Меньше перезагрузок" in text


def test_unknown_build_does_not_invent_changes():
    text = WC.current({"build": 26300, "ubr": 9999, "edition": "Professional"}, D, TODAY)
    assert "нет в моих проверенных данных" in text
    assert "Ближайшая проверенная сборка ниже — 26300.9457" in text


def test_future_platform_build_is_not_a_version():
    text = WC.compare("29613.1000", "26h2", D, "home_pro", TODAY)
    assert "нет в моих проверенных данных" in text


def test_my_build_with_previous_wording_routes_to_current():
    text = WC.answer_compare("сравни мою сборку с прошлой", {"build": 26300, "ubr": 9457, "edition": "Professional"}, D, TODAY)
    assert "Сейчас у тебя Windows 11 26H2" in text


def test_tokens():
    assert WC.find_tokens("сравни 24h2 и 25h2") == ["24h2", "25h2"]
    assert WC.find_tokens("сравни 26300.8697 и 26300.9457") == ["26300.8697", "26300.9457"]


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
