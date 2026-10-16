"""Голос без речи Windows, слово «Мико» не попадает в чат, строки WI во сне выплывают из острова. Без Qt и звука."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import voice as V

def _src(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()

MAIN, UI, WICHAT = _src("main.py"), _src("intel_ui.py"), _src("wichat.py")
VOICE = _src("voice.py")

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

W = V.wake_words_from("мико")

def test_mute_no_windows_speech_anywhere():
    for name, text in (("voice.py", VOICE), ("main.py", MAIN), ("intel_ui.py", UI), ("wichat.py", WICHAT)):
        for bad in ("System.Speech", "SetOutputToDefaultAudioDevice", "powershell", "SpeechRecognitionEngine", "Speaker("):
            check(bad not in text, f"{name}: осталось «{bad}»")
    check("voice_out" not in MAIN and "voice_engine" not in MAIN, "настроек речи вслух и выбора движка нет")

def test_wake_word_is_taken_out_of_the_request():
    check(V.parse_wake("мико открой макс", W) == (True, "открой макс"), "команда без «мико»")
    check(V.parse_wake("Мико, открой макс", W) == (True, "открой макс"), "с запятой")
    check(V.strip_wake("мико открой макс", W) == "открой макс", "текст для запроса без «мико»")

def test_misheard_wake_is_removed_only_inside_open_window():
    # вне окна «ником» — обычное слово, не команда
    check(V.parse_wake("никакой музыки", W) == (False, ""), "вне окна случайное «никакой» не команда")
    # внутри окна (loose) — это слово пробуждения, команда остаётся
    check(V.parse_wake("ником открой макс", W, loose=True) == (True, "открой макс"), "ником → команда")
    check(V.parse_wake("никакой открой макс", W, loose=True) == (True, "открой макс"), "никакой → команда")
    check(V.strip_wake("ником открой макс", W) == "открой макс", "кнопка 🎤 тоже срезает «ником»")

def test_slightly_misheard_wake_inside_window():
    # Vosk слышит «мико» как «мигу» — в окне разговора это то же слово пробуждения
    check(V.parse_wake("мигу как дела", W) == (False, ""), "вне окна «мигу» — не команда (strict)")
    check(V.parse_wake("мигу как дела", W, loose=True) == (True, "как дела"), "в окне «мигу» срезается")
    check(V.parse_wake("привет как дела", W, loose=True) == (False, ""), "обычная фраза не трогается")

def test_wake_only_gives_no_request():
    check(V.parse_wake("мико", W) == (True, ""), "одно слово — пустая команда, в чат не уходит")
    check(V.strip_wake("мико", W) == "", "кнопка: одно «мико» — пустой запрос")

def test_conversation_window_is_respected():
    g = V.ConversationGate(12)
    g.open(100)
    check(g.is_open(105) and not g.is_open(113), "окно разговора работает")

def test_main_uses_wake_logic_and_strips_wake_in_button_path():
    check("loose=in_window" in MAIN, "в окне разговора принимаем искажённое «Мико»")
    check("voice.strip_wake(text" in MAIN, "кнопка 🎤 в чате срезает слово пробуждения")
    check("voice.strip_wake(text" in WICHAT, "кнопка 🎤 в WI срезает слово пробуждения")
    check("def _voice_command" not in MAIN, "голосовых команд речи больше нет")

def test_sleep_bubbles_come_out_of_the_island():
    check("intel_ctl.sub.set_island(sleep_isl)" in MAIN, "островок сна подключён к строкам WI")
    check("def _island_anchor(self)" in UI and "def _emerge(self, isl)" in UI, "строка выплывает из острова")
    check("self._emerge(isl)" in UI and "self.blob.asleep" in UI, "во сне строка появляется из острова")
    check("_slide(QPoint(self._island_target(isl).x(), isl.geometry().center().y()), 260)" in UI,
          "при закрытии втягивается обратно в остров")
    check("_place()" in UI, "вне сна строка по-прежнему встаёт над Mico")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
