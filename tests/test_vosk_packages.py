"""Пакеты Vosk: записаны в зависимости и попадают в сборку exe. Сами пакеты здесь не импортируем."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import voice

def _read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def test_requirements_list_vosk_and_sounddevice():
    req = _read("requirements.txt")
    check("vosk>=" in req and "sounddevice>=" in req, "оба пакета в requirements.txt")

def test_exe_build_collects_their_native_libraries():
    for name in ("build_exe.bat", ".github/workflows/release.yml"):
        s = _read(name)
        check("--collect-all vosk" in s and "--collect-all sounddevice" in s, name)

def test_vosk_check_never_crashes_when_packages_are_missing():
    result = voice.vosk_available()
    check(isinstance(result, bool), "проверка возвращает True/False и не падает")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
