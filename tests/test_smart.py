"""Ответы Mico: вопросы о настройках, вычисления, защита от опасного, короткие ответы, опечатки, база знаний."""
import os as _os, sys, time, types
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for m in ["mss", "psutil", "PIL", "PIL.Image", "requests", "cryptography", "cryptography.fernet"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
sys.modules["cryptography.fernet"].Fernet = object
sys.modules["requests"].RequestException = Exception
import smart as S
import typo as T
import knowledge as K
import notes as N
import phrase as P
import components as C

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def test_toggles_question_gives_sections_not_file_search():
    for q in ["какие настройки ты умеешь переключать?", "какие переключатели есть", "что ты умеешь переключать"]:
        check(S.is_toggle_question(q.lower()), q)
    text = S.toggles_overview(C.TOGGLES)
    check(f"{len(C.TOGGLES)} настроек" in text and "Связь" in text, text[:120])
    check("Нашел" not in text and "Нашёл" not in text, "не должно быть поиска файлов")

def test_calculator():
    check(S.calculate("сколько будет 17 умножить на 23") == "17 * 23 = 391")
    check(S.calculate("10 разделить на 4") == "10 / 4 = 2.5")
    check(S.calculate("2 в степени 10") == "2 ** 10 = 1024")
    check("нельзя" in (S.calculate("10 разделить на 0") or ""), "деление на ноль")
    check(S.calculate("открой блокнот") is None and S.calculate("мне грустно") is None)

def test_safety_refusals_and_no_false_positives():
    for q in ["удали все файлы на диске C", "сотри все данные с компьютера", "отформатируй флешку",
              "сбрось windows до заводских", "очисти диск C"]:
        check(S.safety_refusal(q.lower()), q)
    for q in ["удали все таймеры", "очисти временные файлы", "отмени все таймеры", "открой блокнот"]:
        check(S.safety_refusal(q.lower()) is None, q)

def test_intro_and_capability():
    check(S.is_intro_question("ты кто?") and S.is_intro_question("что ты такое"))
    check(S.capability_question("а ты умеешь музыку включать?") is not None)
    check(S.capability_question("какие настройки ты умеешь переключать") is None, "это вопрос о переключателях")

def test_bare_verbs_ask_what():
    check("Что именно выключить" in S.bare_verb_question("выключи"))
    check("Что именно открыть" in S.bare_verb_question("открой"))
    check(S.bare_verb_question("громче") is None and S.bare_verb_question("заблокируй") is None)

def test_smalltalk_and_crisis():
    check(S.smalltalk("спасибо!")[1] == "happy")
    check(S.smalltalk("ты молодец 😊")[1] == "proud")
    check(S.smalltalk("мне грустно")[1] == "sad")
    check(S.smalltalk("я не хочу жить")[0].startswith("Мне важно"), "кризис — поддержка, не шутка")

def test_typo_keeps_common_words_and_fixes_real_typos():
    c = T.Corrector(None, ())
    check(c.correct("что такое брандмауэр")[0] == "что такое брандмауэр")
    check(c.correct("запомни: купить молоко")[0] == "запомни: купить молоко", "запомни не превращаем в напомни")
    check(c.correct("какой у меня процессор")[0] == "какой у меня процессор")
    check(c.correct("откртой блокнот")[0] == "открой блокнот", "настоящая опечатка исправляется")

def test_knowledge_matches_real_topics():
    items = K.load(_os.path.join(ROOT, "knowledge"))
    check((K.answer("как работает режим тишины", items) or "").startswith("Режим тишины"))
    check((K.answer("что такое помодоро", items) or "").startswith("Помодоро"))
    check((K.answer("что такое OneDrive", items) or "").startswith("OneDrive"))
    check((K.answer("что такое брандмауэр", items) or "").startswith("Брандмауэр"))

def test_notes_with_colon_and_plain():
    check(N.parse("запомни: купить молоко") == ("add", "купить молоко"))
    check(N.parse("Запиши молоко") == ("add", "молоко"))
    check(N.parse("запомни рабочее место") is None, "рабочее место — не заметка")

def test_greeting_matches_what_user_said():
    check(P.greeting_kind("доброе утро!") == "morning" and P.greeting_kind("добрый вечер 😊") == "evening")
    check(P.greeting_text(kind="night").split("!")[0] in ("Доброй ночи", "Не спится? Доброй ночи"))
    check(P.greeting_kind("привет") is None, "без времени суток — по часам")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
