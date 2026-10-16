"""Четвёртый раунд: вкладка «Голос», модель Vosk, прозрачность волн, пометка BETA, без плашки «слушаю». Без Qt."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import voice as V
import voicemodel as M

MAIN = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
UI = open(_os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def test_status_capsule_is_gone():
    check("self.island = None" in UI and "Island(cfg, blob)" not in UI, "плашка «слушаю» не создаётся")

def test_wave_opacity_setting_and_presets():
    check('"wave_opacity": 85' in MAIN, "прозрачность волн — настройка по умолчанию 85")
    check("b_clear = QPushButton(\"Максимально прозрачные\")" in MAIN, "кнопка «максимально прозрачные»")
    check("b_solid = QPushButton(\"Непрозрачные\")" in MAIN, "кнопка «непрозрачные»")
    check("wave_opacity=self.wave_op.value()" in MAIN, "значение сохраняется")

def test_voice_has_its_own_tab_with_flexible_settings():
    check('tabs.addTab(page((self._voice_box(cfg), "Голос и речь")), "Голос")' in MAIN, "вкладка «Голос»")
    for key in ["voice_listen", "voice_wake", "wake_words", "conversation_sec", "min_confidence", "vosk_model_dir"]:
        check(f'"{key}"' in MAIN, key)

def test_model_buttons_exist_and_report_failures():
    check('b_dl = QPushButton("Скачать модель")' in MAIN and 'b_file = QPushButton("Выбрать файл вручную…")' in MAIN,
          "две кнопки: скачать и выбрать вручную")
    check("voicemodel.fetch_model(APPDIR" in MAIN and "Можно выбрать файл вручную" in MAIN,
          "при неудаче причина и предложение файла вручную")

def test_beta_is_marked_for_windows_intelligence():
    check("Mico · WI (BETA)" in MAIN, "пункт выбора режима помечен BETA")
    check('"Mico · WI (BETA)"' in MAIN, "вкладка помечена BETA")

def test_wake_words_and_confidence_come_from_settings():
    check(V.wake_words_from("мико, микро") == ("мико", "mico"), "слова пробуждения фиксированы: мико и mico")
    check(V.parse_wake("mico открой блокнот", V.wake_words_from("мико, микро")) == (True, "открой блокнот"))
    check(V.accept_phrase("открой", 0.6, 0.7) is False, "порог из настроек, а не жёсткий")
    check("voice.wake_words_from(self.cfg.get(\"wake_words\"))" in MAIN, "слова пробуждения из настроек")

def test_vosk_model_helpers_detect_structure():
    import tempfile
    root = tempfile.mkdtemp()
    check(not M.is_installed(root), "пустая папка — не модель")
    model = _os.path.join(root, "m")
    _os.makedirs(_os.path.join(model, "am"))
    _os.makedirs(_os.path.join(model, "graph"))
    open(_os.path.join(model, "am", "final.mdl"), "wb").write(b"x")
    check(M.is_installed(model), "модель с am/final.mdl и graph")

def test_vosk_listener_only_used_when_package_present():
    check("problem = voice.vosk_problem(model)" in MAIN and "VoskListener(model" in MAIN,
          "Vosk включается только если пакеты и модель на месте")
    check("self.mic_error.emit(problem)" in MAIN, "если Vosk не готов — причина показывается в чате")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
