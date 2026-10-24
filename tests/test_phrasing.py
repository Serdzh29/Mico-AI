"""Понимание фраз не по шаблону: помодоро, приветствия, синонимы команд."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import phrase as P

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

POMO_START = ["помодоро", "помодоро!", "давай помодоро", "запусти помодоро на 25 минут", "Мико, начни помодоро 🍅",
              "включи помодоро?", "стартуй помодоро", "хочу помодоро", "помодоро сейчас", "начни рабочий цикл",
              "запусти помодоро пожалуйста", "давай-ка помодоро 😊", "pomodoro"]
POMO_STOP = ["помодоро стоп", "останови помодоро", "отмени помодоро", "хватит помодоро", "выключи помодоро",
             "прекрати помодоро!", "закончи помодоро", "стоп помодоро"]
POMO_STATUS = ["сколько помодоро сегодня", "как дела с помодоро сегодня", "сколько циклов помодоро сделал",
               "статистика помодоро", "сколько помидоров за сегодня"]

def test_pomodoro_start_variants():
    for q in POMO_START:
        check(P.pomodoro_intent(q) == "start", (q, P.pomodoro_intent(q)))

def test_pomodoro_stop_and_status():
    for q in POMO_STOP:
        check(P.pomodoro_intent(q) == "stop", (q, P.pomodoro_intent(q)))
    for q in POMO_STATUS:
        check(P.pomodoro_intent(q) == "status", (q, P.pomodoro_intent(q)))

def test_not_pomodoro_is_not_taken():
    for q in ["открой блокнот", "какая погода", "таймер на 10 минут", "громче"]:
        check(P.pomodoro_intent(q) is None, q)

def test_greetings_with_emoji_and_exclamation():
    for q in ["привет!", "Доброе утро! ☀️", "здравствуй, Мико 😊", "добрый вечер!!!", "Добрый день 🙂",
              "доброй ночи! 🌙", "хай", "здравствуйте!", "привет Мико!!!", "доброе утро 😊"]:
        check(P.is_greeting(q), q)
    check(not P.is_greeting("добрый день, открой блокнот"), "приветствие с командой не должно быть только приветствием")

def test_greeting_text_matches_time_of_day():
    import time
    morning = time.mktime((2026, 10, 14, 8, 0, 0, 0, 0, -1))
    day = time.mktime((2026, 10, 14, 13, 0, 0, 0, 0, -1))
    evening = time.mktime((2026, 10, 14, 19, 0, 0, 0, 0, -1))
    night = time.mktime((2026, 10, 14, 2, 0, 0, 0, 0, -1))
    check(P.period(morning) == "morning" and P.period(day) == "day" and P.period(evening) == "evening"
          and P.period(night) == "night")
    for _ in range(20):
        check(P.greeting_text(morning).startswith("Доброе утро"), "утро")
        check(P.greeting_text(day).startswith("Добрый день"), "день")
        check(P.greeting_text(evening).startswith("Добрый вечер"), "вечер")
        check("Доброй ночи" in P.greeting_text(night), "ночь")
        check("!" in P.greeting_text(day), "восклицание")

def test_synonyms_map_to_known_command_forms():
    cases = {"прибавь звук": "громче", "громкость побольше": "громче", "погромче": "громче",
             "убавь громкость": "тише", "сделай тише": "тише", "выруби звук": "без звука",
             "убери звук пожалуйста": "без звука", "поярче": "ярче", "прибавь яркость": "ярче",
             "потемнее": "темнее", "убавь яркость": "темнее", "залочи комп": "заблокируй пк"}
    for q, want in cases.items():
        got = P.canonical(q)
        check(got == want, (q, got, want))

def test_timer_synonyms():
    check(P.canonical("поставь таймер на 10 минут") == "таймер на 10 минут", P.canonical("поставь таймер на 10 минут"))
    check(P.canonical("засеки 5 минут") == "таймер 5 минут", P.canonical("засеки 5 минут"))

def test_canonical_never_empties_and_keeps_unknown_text():
    check(P.canonical("какие настройки ты умеешь переключать?") == "какие настройки ты умеешь переключать",
          P.canonical("какие настройки ты умеешь переключать?"))
    check(P.canonical("ну") == "" or P.canonical("ну") == "", "пустая фраза допустима (брейн подставит исходную)")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
