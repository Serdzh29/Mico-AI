"""Память о себе: то, что пользователь сказал прямо в чате (user_profile.py). Без Qt и модели.
Запуск: python tests/test_self_memory.py"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from data import profile as U


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_explicit_self_statements_are_recognised():
    text, explicit = U.parse_self_statement("меня зовут Сергей")
    check(text == "Пользователя зовут Сергей" and explicit is False, text)
    text, explicit = U.parse_self_statement("я работаю программистом на Python")
    check("программистом" in text and explicit is False, text)
    text, explicit = U.parse_self_statement("запомни, что у меня собака Рекс")
    check(explicit is True and "собака" in text, text)


def test_small_talk_and_temporary_states_are_not_stored():
    for q in ("я устал сегодня", "я болею гриппом", "открой браузер", "я не знаю", "мне грустно"):
        check(U.parse_self_statement(q) is None, f"не должно попасть в память: {q}")


def test_sensitive_self_statements_are_not_stored():
    check(U.parse_self_statement("я работаю в банке, мой пароль 1234") is None, "пароль — никогда")
    check(U.parse_self_statement("я работаю и живу на улице Ленина") is None, "адрес — никогда")
    check(U.parse_self_statement("я работаю и у меня двое детей") is None, "семья — никогда")
    check(U.parse_self_statement("запомни, что я болею астмой") is None, "здоровье — никогда")
    check(U.parse_self_statement("я люблю тебя, ты классный") is None, "фразы про собеседника — не о пользователе")


def test_self_fact_is_confirmed_and_survives_auto_refresh():
    p = U.empty()
    text, _ = U.parse_self_statement("я люблю рисовать акварелью")
    p = U.add_self_fact(p, U.self_fact(text))
    fact = p["facts"][0]
    check(fact["status"] == U.CONFIRMED and "self" in fact["tags"], fact)
    p = U.merge(p, [])                                    # ежечасный пересчёт не должен стереть факт
    check(any(f["key"] == fact["key"] for f in p["facts"]), "факт о себе пережил пересчёт")


def test_self_fact_is_used_in_prompt_even_for_unrelated_question():
    p = U.add_self_fact(U.empty(), U.self_fact("Пользователя зовут Сергей"))
    picked = U.relevant(p, "какая завтра погода?")
    check(len(picked) == 1 and "Сергей" in picked[0]["text"], picked)
    check("Сергей" in U.prompt_line(picked))


def test_forgotten_fact_comes_back_only_when_user_says_it_again():
    p = U.add_self_fact(U.empty(), U.self_fact("Пользователь сказал: «я читаю фантастику»"))
    p, _ = U.apply_command(p, "forget", 1)                 # «забудь факт 1»
    check(p["facts"] == [], "факт забыт")
    p = U.add_self_fact(p, U.self_fact("Пользователь сказал: «я читаю фантастику»"))
    check(len(p["facts"]) == 1 and p["forgotten"] == [], "сказал снова — факт вернулся")


def test_topic_facts_still_work_as_before():
    p = U.merge(U.empty(), None, U.candidate_facts(["Работаю программистом на Python"]))
    check(U.relevant(p, "что делать программисту на Python?") == [], "ждущие подтверждения не в промпт")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK self_memory")
