"""Микрофон и ползунок волн: ошибки видны человеку, ползунок меняет волны сразу. Без Qt и звука."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import voice as V

MAIN = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
WICHAT = open(_os.path.join(ROOT, "wichat.py"), encoding="utf-8").read()

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def test_chat_shows_the_reason_when_mic_fails():
    check("self._mic_error = err" in MAIN and "self.say(self._mic_error" in MAIN, "главный чат показывает причину")
    check("self._mic_error = err" in WICHAT and "self._mic_error or" in WICHAT, "WI показывает причину в поле ввода")

def test_wave_slider_applies_live():
    check("self.wave_op.valueChanged.connect(self._live_wave)" in MAIN, "ползунок подключён")
    check("def _live_wave(self, value):" in MAIN and 'self.cfg["wave_opacity"] = int(value)' in MAIN,
          "значение сразу в настройках")
    check("glow.update()" in MAIN, "полоса перерисовывается сразу")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
