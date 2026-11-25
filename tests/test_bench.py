"""Набор запросов для замера моделей и оценка ответов. Без сети и без Ollama."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bench"))
sys.path.insert(0, ROOT)
import scoring as S
from win import osagent as O


def test_prompt_set_is_fixed_size_and_valid():
    ps = S.load_prompts()
    assert 20 <= len(ps) <= 30, "по плану — от 20 до 30 запросов"
    assert len({p["id"] for p in ps}) == len(ps), "идентификаторы уникальны"
    for p in ps:
        assert p["category"] in S.CATEGORIES, p["id"]
        assert p["prompt"].strip(), p["id"]
        if p["category"] == "action":
            assert p.get("expect") in O.CATALOG, f"{p['id']}: действие должно быть в каталоге osagent"
        else:
            assert "expect" not in p


def test_all_categories_are_represented():
    cats = {p["category"] for p in S.load_prompts()}
    assert cats == set(S.CATEGORIES), cats


def test_good_russian_answer_passes():
    p = {"id": "x", "category": "chat", "prompt": "q", "must": ["391"]}
    assert S.check_reply(p, "17 умножить на 23 будет 391.") == []


def test_english_reasoning_and_think_tags_fail():
    p = {"id": "x", "category": "chat", "prompt": "q"}
    assert S.check_reply(p, "The user asks a question about weather.")
    assert S.check_reply(p, "<think>ладно</think> Ответ")


def test_missing_expected_word_fails():
    p = {"id": "x", "category": "chat", "prompt": "q", "must": ["391"]}
    assert any("391" in r for r in S.check_reply(p, "Не знаю."))


def test_empty_answer_fails():
    assert S.check_reply({"id": "x", "category": "chat", "prompt": "q"}, "  ") == ["пустой ответ"]


def test_action_answer_must_be_valid_call_with_expected_name():
    p = {"id": "a", "category": "action", "prompt": "громкость 30", "expect": "set_volume"}
    assert S.check_reply(p, '{"action": "set_volume", "args": {"percent": 30}}') == []
    assert S.check_reply(p, "Громкость увеличу, сейчас.")                      # нет JSON
    assert any("ожидали" in r for r in S.check_reply(p, '{"action": "open_app", "args": {"name": "x"}}'))


def test_summary_medians_and_category_rates():
    rows = [
        {"category": "chat", "auto_ok": True, "ttft_ms": 100, "tok_s": 20.0, "total_s": 2.0},
        {"category": "chat", "auto_ok": False, "ttft_ms": 300, "tok_s": 10.0, "total_s": 4.0},
        {"category": "action", "auto_ok": True, "ttft_ms": None, "tok_s": None, "total_s": 1.0},
    ]
    s = S.summarize(rows)
    assert s["n"] == 3 and s["auto_pass_pct"] == 66.7
    assert s["ttft_ms_median"] == 200 and s["tok_s_median"] == 15.0
    assert s["by_category"] == {"chat": 50.0, "action": 100.0}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK bench")
