"""Смысловое вспоминание: тема находится по формам слов и близким словам, а не только буквально.
«Про вчерашний созвон» находит реплики про встречу — это поведение, а не строки кода."""
import os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import recall as R

DAY = 86400


def test_word_forms_score_full_match():
    assert R.score("как настроить принтера", ["принтер"]) >= 1.0
    assert R.score("настроили принтеры в офисе", ["принтер"]) >= 1.0


def test_near_words_find_each_other():
    rows = [(1, "user", "на встрече обсуждали бюджет"), (2, "mico", "Обсудили смету"),
            (3, "user", "какая погода"), (4, "mico", "Облачно")]
    now = time.time()
    spec = {"label": "за последнюю неделю", "topic": ["созвон"]}
    text = R.answer(rows, spec)
    assert "встрече" in text, "созвон находит встречу — близкие слова"
    assert "погода" not in text, "посторонние реплики не проходят"


def test_unrelated_words_do_not_match():
    assert R.score("какая погода на выходных", ["принтер"]) < R.MATCH


def test_mentions_keeps_old_behaviour_for_exact_topics():
    assert R._mentions("как настроить принтер", ["принтер"])
    assert not R._mentions("какая погода", ["принтер"])


def test_parse_still_understands_questions():
    now = time.time()
    assert R.parse("вспомни про вчерашний созвон", now)["topic"] == ["созвон"]
    assert R.parse("что я делал час назад", now) is None


if __name__ == "__main__":
    for n, fn in sorted(list(globals().items())):
        if n.startswith("test_") and callable(fn):
            fn()
            print("OK", n)
    print("ALL OK recall semantic")
