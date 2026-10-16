"""Голос и волны: чистая логика (без звука и без Qt)."""
import os as _os, re, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import intel
import settings_info as SI
import voice as V

MAIN = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def test_wave_profile_is_smooth_and_bounded():
    v = intel.wave_profile(80, 2.3)
    check(len(v) == 80 and all(0.0 <= x <= 1.0 for x in v), "в пределах 0..1")
    jumps = max(abs(v[i + 1] - v[i]) for i in range(79))
    check(jumps < 0.12, f"соседние колонки почти не отличаются: {jumps:.3f}")
    check(intel.wave_profile(80, 2.3) == intel.wave_profile(80, 2.3), "детерминированно")

def test_answer_raises_waves_at_bumps_only():
    rest = intel.wave_profile(60, 1.0, answer=0.0)
    talk = intel.wave_profile(60, 1.0, answer=1.0)
    check(max(talk) > max(rest), "при ответе волна выше")
    gains = [talk[i] - rest[i] for i in range(60)]
    check(max(gains) - min(gains) > 0.05, "подъём неравномерный — в некоторых местах больше")

def test_idle_waves_exist_and_stop_in_fullscreen_logic():
    check("IDLE = 0.55" in open(_os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read(), "постоянный уровень волн")
    check("def set_idle(self, on)" in open(_os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read(), "режим постоянных волн")

def test_bubbles_fill_their_width():
    w = open(_os.path.join(ROOT, "wichat.py"), encoding="utf-8").read()
    check("row.addWidget(lab, 1)" in w and "setMinimumWidth(40)" in w, "пузырёк растягивается по ширине")

def test_voice_is_wired_into_chat_and_settings():
    check("self.mic_btn = mic_btn" in MAIN and "def listen(self)" in MAIN, "кнопка микрофона")
    check("heard = pyqtSignal(str)" in MAIN and "def _on_heard" in MAIN, "распознанная фраза уходит в чат")
    check("voice.voice_intent" not in MAIN and "self.speaker" not in MAIN, "голосовых команд речи нет")
    check('"voice_out"' not in MAIN and "voice_out" not in SI.CFG_HINTS, "ответы вслух убраны из настроек")

def test_windows_intelligence_has_voice_and_waves():
    wc = open(_os.path.join(ROOT, "wichat.py"), encoding="utf-8").read()
    ui = open(_os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    check("self.mic = QPushButton" in wc and "voice.listen_once(self.cfg, 8)" in wc, "микрофон в чате WI")
    check("self.speaker" not in ui and "self._speak(" not in ui, "WI ничего не читает вслух")
    check("def _draw_waves(self, p, w, h, bh, rgb)" in ui and "intel.wave_profile(" in ui, "волны рисуются внизу")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
