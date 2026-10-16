"""Бета: обращение «Мико» не попадает в запрос, «никакой» в начале — тоже обращение (только в этом смысле),
лишний вызов Vosk-модели не делается, ошибки микрофона доходят до чата. Без Qt и микрофона."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import json
import voice as V

def _src(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()

MAIN, VOICE = _src("main.py"), _src("voice.py")
W = V.WAKE_WORDS

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def test_mishear_forms_are_all_known():
    for form in ("никакой", "никакого", "никакому", "никакое", "никакую", "никаким", "никакие", "никаких", "никому", "ником"):
        check(form in V.WAKE_MISHEARD, form)

def test_wake_grammar_contains_words_mishears_and_unk():
    g = json.loads(V.wake_grammar("мико, микро"))
    check("мико" in g and "mico" in g and "никакой" in g and "[unk]" in g, g)
    check(len(g) == len(set(g)), "без повторов")

def test_heard_wake_checks_first_word_only():
    check(V.heard_wake("никакой"), "искажение в начале — обращение")
    check(V.heard_wake("мико"), "точное слово")
    check(V.heard_wake("[unk] мико"), "служебный [unk] пропускаем")
    check(not V.heard_wake("ну мико открой"), "ну мико — не обращение")
    check(not V.heard_wake("я сказал никакой"), "никакой не в начале — не обращение")
    check(not V.heard_wake(""), "пусто")
    check(not V.heard_wake("микро открой", "мико, микро"), "слова фиксированы: микро — не обращение")
    check(V.heard_wake("mico открой", "мико, микро"), "mico всегда работает")

def test_address_is_removed_from_request_for_all_forms():
    check(V.strip_wake("никакой открой блокнот", W) == "открой блокнот", "кнопка 🎤: искажение срезается")
    check(V.parse_wake("никакого открой блокнот", W, loose=True) == (True, "открой блокнот"))
    check(V.parse_wake("Мико, открой блокнот", W) == (True, "открой блокнот"))

def test_wake_grammar_and_heard_wake_wired_into_listener():
    check("wake_grammar(self.wake_words)" in VOICE, "отдельный распознаватель получает искажения")
    check("if heard_wake(said, words):" in VOICE, "проверка по первому слову")

def test_model_is_loaded_once_and_cached():
    check("_MODEL_CACHE" in VOICE and "def load_model" in VOICE, "кэш модели")
    check("model = load_model(model_dir)" in VOICE or "model = load_model(self.model_dir)" in VOICE, "слушатель берёт кэш")
    check("model = load_model(model_dir)" in VOICE, "разовое нажатие 🎤 тоже берёт кэш")

def test_listener_errors_reach_chat():
    check("def _run_safe" in VOICE and "self.on_error(" in VOICE, "поток не умирает молча")
    check("wake_words=words, on_error=self.mic_error.emit" in MAIN, "ошибка уходит в чат")

def test_no_windows_speech_or_engine_choice_left():
    for bad in ("voice_out", "voice_engine", "Отвечать голосом", "Скорость голоса", "Встроенный Windows"):
        check(bad not in MAIN and bad not in VOICE, bad)

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("ok")
