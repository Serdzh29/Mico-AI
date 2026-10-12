"""Программа предварительной оценки: какая сборка считается бетой, согласие, приветствие и замена exe."""
import json, os, re, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import betaprogram as B
import features as F

GOOD_BETA = {"version": "2026.10.1300", "url": "https://example.com/Mico-beta.exe", "sha256": "abc123", "notes": ""}


def _file(channels):
    return json.dumps({"version": "2026.10.1217", "url": "https://example.com/Mico.exe", "sha256": "stab",
                       "channels": channels})


def test_beta_build_takes_only_explicit_beta_channel():
    # без канала beta бета-сборкой не становится даже стабильный файл
    try:
        B.beta_build(json.dumps({"version": "1", "url": "https://x/y.exe", "sha256": "s"}))
        raise AssertionError("бета выдана без канала beta")
    except B.BetaUnavailable:
        pass
    info = B.beta_build(_file({"stable": {"version": "1", "url": "https://x/s.exe", "sha256": "s"},
                               "beta": GOOD_BETA}))
    assert info["version"] == "2026.10.1300" and info["url"].startswith("https://")


def test_beta_build_requires_https_and_checksum():
    for bad in ({"url": "http://x/b.exe", "sha256": "s"}, {"url": "https://x/b.exe", "sha256": ""}):
        try:
            B.beta_build(_file({"beta": {"version": "2", **bad}}))
            raise AssertionError(f"принята плохая бета: {bad}")
        except B.BetaUnavailable:
            pass


def test_consent_is_new_and_covers_errors_and_beta_use():
    assert F.BETA_CONSENT_VERSION >= 2
    assert not B.consent_given({"beta_consent_version": 1})          # старое согласие не считается
    assert B.consent_given({"beta_consent_version": F.BETA_CONSENT_VERSION})
    text = F.BETA_CONSENT_TEXT.lower()
    assert "ошибки" in text and "бета-функциями" in text and "разработчику" in text
    assert "сам" in text                                              # отправка по действию человека


def test_welcome_lists_every_beta_feature_with_its_explanation():
    lines = B.welcome_lines("2026.10.1300 бета")
    joined = "\n".join(lines)
    assert "бета" in lines[0]
    for _, item in B.beta_feature_list():
        assert any(item["title"] in l and item["explain"] in l for l in lines), item["title"]
    assert joined.count("•") == len(B.beta_feature_list())


def test_welcome_runs_once_per_beta_install():
    assert B.needs_welcome({"update_channel": "beta"})
    assert not B.needs_welcome({"update_channel": "beta", "beta_welcome_version": F.BETA_WELCOME_VERSION})
    assert not B.needs_welcome({"update_channel": "stable"})


def test_replace_waits_for_busy_file_then_copies():
    import builtins
    d = tempfile.mkdtemp()
    src, dest = os.path.join(d, "new.exe"), os.path.join(d, "Mico.exe")
    open(src, "wb").write(b"NEW")
    open(dest, "wb").write(b"OLD")
    real_open = builtins.open
    busy = {"left": 2}                                  # первые две попытки «старая копия ещё работает»

    def guarded(path, mode="r", *a, **k):
        if path == dest and "a" in mode and busy["left"] > 0:
            busy["left"] -= 1
            raise PermissionError("занято")
        return real_open(path, mode, *a, **k)
    builtins.open = guarded
    try:
        ok = B.replace_when_free(src, dest, tries=5, pause=0, sleep=lambda _: None)
    finally:
        builtins.open = real_open
    assert ok and real_open(dest, "rb").read() == b"NEW" and busy["left"] == 0


def test_replace_gives_up_when_never_free():
    d = tempfile.mkdtemp()
    src = os.path.join(d, "new.exe")
    open(src, "wb").write(b"NEW")
    dest = os.path.join(d, "dir_instead_of_file")
    os.makedirs(dest)                                              # открыть каталог на запись нельзя
    assert B.replace_when_free(src, dest, tries=3, pause=0, sleep=lambda _: None) is False


def test_join_flag_detected():
    assert B.is_join_request(["Mico.exe", B.JOIN_FLAG])
    assert not B.is_join_request(["Mico.exe"])


def test_wizard_has_no_beta_checkbox_and_no_consent_bypass():
    src = open(os.path.join(ROOT, "installer.py"), encoding="utf-8").read()
    assert "opt_beta" not in src
    assert re.search(r'update_channel="stable"', src)
    assert "update_channel=\"beta\" if beta" not in src


def test_spin_animation_exists_and_is_not_random_idle():
    src = open(os.path.join(ROOT, "blob.py"), encoding="utf-8").read()
    assert '"spin": 2.2' in src
    assert 'random.choice(["lookaround", "blink2", "wink"])' in src   # без «spin», прыжков и сердечка в случайных


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("OK test_beta_program")
