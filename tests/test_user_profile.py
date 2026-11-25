"""Портрет пользователя (user_profile.py): пороги, источники, что попадает в промпт, команды.
Без Qt, Windows и модели. Запуск: python tests/test_user_profile.py"""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from data import profile as U

NOW = time.time()
DAY = 86400


def _day_rows(proc, days, secs=900):
    return [(NOW - d * DAY, NOW - d * DAY + secs, proc) for d in days]


def test_program_becomes_fact_only_after_repeats():
    rows = _day_rows("chrome.exe", [0, 1, 2])
    facts = U.program_facts(rows)
    assert len(facts) == 1 and facts[0]["key"] == "prog:chrome.exe"
    assert "browser" in facts[0]["tags"] and facts[0]["status"] == U.CONFIRMED
    assert U.program_facts(_day_rows("chrome.exe", [0, 1])) == [], "два дня — ещё не привычка"


def test_short_use_and_system_processes_are_ignored():
    assert U.program_facts(_day_rows("notepad.exe", [0, 1, 2], secs=60)) == [], "меньше 10 минут в день не считаем"
    assert U.program_facts(_day_rows("explorer.exe", [0, 1, 2])) == [], "системные процессы не в профиле"
    assert U.program_facts(_day_rows("mico.exe", [0, 1, 2])) == [], "сам Mico AI не в профиле"


def test_chip_facts_need_repeats_and_known_label():
    facts = U.chip_facts({"screen": 3, "vol_up": 2, "ghost": 9}, {"screen": "Что на экране?", "vol_up": "Громче"})
    assert [f["key"] for f in facts] == ["chip:screen"]


def test_parse_candidates_filters_garbage_and_sensitive():
    raw = ('Вот: {"facts": ["Работаю программистом на Python", "мой пароль 1234", "ок", '
           '"Живу в Казани, адрес ул. Ленина 5", 42, "Пользуюсь Obsidian для заметок"]}')
    got = U.parse_candidates(raw)
    assert "Работаю программистом на Python" in got
    assert "Пользуюсь Obsidian для заметок" in got
    assert all("пароль" not in g and "адрес" not in g for g in got)
    assert U.parse_candidates("не JSON вообще") == []
    assert U.parse_candidates('{"facts": "не список"}') == []


def test_candidates_wait_for_confirmation_and_stay_out_of_prompt():
    p = U.merge(U.empty(), [], U.candidate_facts(["Работаю программистом на Python"]))
    assert p["facts"][0]["status"] == U.PENDING
    assert U.relevant(p, "программистом на Python") == [], "ждущий подтверждения факт не идёт в промпт"
    res, text = U.apply_command(p, "confirm", 1)
    assert res["facts"][0]["status"] == U.CONFIRMED and "Подтвердил" in text
    assert len(U.relevant(res, "что делать программисту на Python?")) == 1


def test_merge_keeps_auto_facts_when_no_auto_given():
    p = U.merge(U.empty(), U.program_facts(_day_rows("chrome.exe", [0, 1, 2])))
    p = U.merge(p, None, U.candidate_facts(["Изучаю Rust"]))
    assert any(f["key"] == "prog:chrome.exe" for f in p["facts"]), "добавление факта не должно стирать автофакты"


def test_facts_below_threshold_disappear_on_refresh():
    p = U.merge(U.empty(), U.program_facts(_day_rows("chrome.exe", [0, 1, 2])))
    p = U.merge(p, U.program_facts(_day_rows("chrome.exe", [0, 1])))      # в журнале осталось два дня
    assert not any(f["key"] == "prog:chrome.exe" for f in p["facts"])


def test_forgotten_fact_does_not_come_back():
    p = U.merge(U.empty(), U.program_facts(_day_rows("chrome.exe", [0, 1, 2])))
    p, text = U.apply_command(p, "forget", 1)
    assert "Забыл" in text and p["facts"] == []
    p = U.merge(p, U.program_facts(_day_rows("chrome.exe", [0, 1, 2, 3])))
    assert p["facts"] == [], "удалённое пользователем не возвращается само"


def test_browser_question_gets_browser_fact_and_unrelated_gets_nothing():
    p = U.merge(U.empty(), U.program_facts(_day_rows("msedge.exe", [0, 1, 2])))
    assert [f["key"] for f in U.relevant(p, "открой браузер")] == ["prog:msedge.exe"]
    assert U.preferred_browser(p) == "edge"
    assert U.relevant(p, "включи тишину") == [], "«включи тишину» — ничего лишнего"
    assert U.prompt_line(U.relevant(p, "включи тишину")) == ""


def test_at_most_limit_facts_in_prompt():
    rows = _day_rows("chrome.exe", [0, 1, 2]) + _day_rows("firefox.exe", [0, 1, 2]) + _day_rows("opera.exe", [0, 1, 2])
    p = U.merge(U.empty(), U.program_facts(rows))
    assert len(U.relevant(p, "открой браузер")) <= U.MAX_IN_PROMPT


def test_profile_commands_parse():
    assert U.parse_command("что ты обо мне знаешь?") == ("list", None)
    assert U.parse_command("Что ты знаешь обо мне") == ("list", None)
    assert U.parse_command("подтверди факт 2") == ("confirm", 2)
    assert U.parse_command("забудь факт 3") == ("forget", 3)
    assert U.parse_command("забудь всё обо мне") == ("forget_all", None)
    assert U.parse_command("открой браузер") is None
    assert U.parse_command("что я делал вчера") is None


def test_list_and_numbers_out_of_range():
    assert "Пока ничего" in U.describe_list(U.empty())
    p, text = U.apply_command(U.empty(), "forget", 5)
    assert "Нет факта с номером 5" in text


def test_forget_all_clears_and_blocks_current_facts():
    p = U.merge(U.empty(), U.program_facts(_day_rows("chrome.exe", [0, 1, 2])))
    p, text = U.apply_command(p, "forget_all")
    assert p["facts"] == [] and "Забыл всё" in text
    assert "prog:chrome.exe" in p["forgotten"]


def test_limit_on_pending_facts():
    texts = [f"Факт номер {i} про работу" for i in range(20)]
    p = U.merge(U.empty(), None, U.candidate_facts(texts))
    assert sum(1 for f in p["facts"] if f["status"] == U.PENDING) <= U.MAX_PENDING


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK user_profile")
