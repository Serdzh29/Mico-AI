"""Третий раунд: волны, остров сна, постоянное прослушивание «Мико» и качество диктовки. Без Qt."""
import os as _os, sys, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import voice as V

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def _src(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()

def test_dictation_is_written_neatly():
    check(V.normalize_dictation("что такое брандмауэр") == "Что такое брандмауэр?", V.normalize_dictation("что такое брандмауэр"))
    check(V.normalize_dictation("открой   блокнот") == "Открой блокнот.")
    check(V.normalize_dictation("уже с точкой!") == "Уже с точкой!")
    check(V.normalize_dictation("") == "")

def test_wake_word_and_command_split():
    check(V.parse_wake("Мико, открой ютуб") == (True, "открой ютуб"))
    check(V.parse_wake("мико") == (True, ""), "только слово — ждём команду")
    check(V.parse_wake("открой мико") == (False, ""), "слово в конце — не пробуждение")

def test_unsure_phrases_are_dropped():
    check(V.accept_phrase("открой блокнот", 0.9) is True)
    check(V.accept_phrase("открой блокнот", 0.3) is False, "низкая уверенность — не выполняем")
    check(V.accept_phrase("", 0.99) is False, "пустая фраза не нужна")

def test_conversation_window_lets_follow_ups_through():
    g = V.ConversationGate(window=12)
    check(not g.is_open(100), "до команды окна нет")
    g.open(100)
    check(g.is_open(105) and not g.is_open(113), "окно 12 секунд после команды")

def test_island_appears_where_mico_was_and_wakes_on_click():
    s = _src("sleep_island.py")
    check("class SleepIsland" in s and "wake = pyqtSignal()" in s, "островок и сигнал пробуждения")
    check("OutCubic" in s and "b\"geometry\"" in s, "вырастает из Mico плавно (геометрия)")
    check("mousePressEvent" in s and "self.wake.emit()" in s, "клик будит")
    m = _src("main.py")
    check("sleep_isl.show_from(blob)" in m and "blob.hide()" in m, "Mico при сне превращается в островок")
    check("sleep_isl.wake.connect(lambda: (blob.show(), blob.wake()))" in m, "клик по островку возвращает Mico")
    check("blob.awake.connect(lambda: sleep_isl.retract_to(blob))" in m, "при пробуждении островок втягивается в Mico")

def test_waves_are_less_transparent_and_smoother():
    ui = _src("intel_ui.py")
    check("a_bot" in ui and "round(255 * k)" in ui and "wave_opacity" in ui, "прозрачность волн — из настроек")
    check("quadTo(" in ui and "layer(1.7" in ui and "layer(0.0" in ui, "две волны, плавные кривые")

def test_background_listening_is_opt_in_and_ignores_own_voice():
    m = _src("main.py")
    check('"voice_wake": False' in m, "фоновое прослушивание выключено по умолчанию")
    check("if self.busy:" in m and "self.speaker" not in m, "во время ответа не слушаем, речи вслух нет")
    check("self.panel.apply_voice()" in m and "def apply_voice(self):" in m, "включение и выключение после «Сохранить»")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
