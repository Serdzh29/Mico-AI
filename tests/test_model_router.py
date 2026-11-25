"""Роутер fast/deep: глубокие вопросы — умной модели, быстрые — лёгкой.
Пока установлена одна модель — роутер ничего не меняет (это тоже проверяем)."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from llm import catalog


def test_one_model_is_always_the_answer():
    assert catalog.route("объясни квантовую физику", ["qwen3.5-4b"], "qwen3.5-4b") == "qwen3.5-4b"
    assert catalog.route("привет", ["qwen3.5-4b"]) == "qwen3.5-4b"


def test_no_models_gives_none_or_preferred():
    assert catalog.route("привет", []) is None
    assert catalog.route("привет", [], "qwen3.5-4b") == "qwen3.5-4b"


def test_deep_questions_go_to_preferred_model():
    ids = ["qwen3.5-4b", "qwen2.5-3b"]
    assert catalog.route("объясни, как работает память", ids, "qwen3.5-4b") == "qwen3.5-4b"
    assert catalog.route("напиши план поездки подробно", ids, "qwen3.5-4b") == "qwen3.5-4b"
    assert catalog.route("х" * 120, ids, "qwen3.5-4b") == "qwen3.5-4b", "длинный вопрос — глубокий"


def test_quick_questions_go_to_fast_model():
    ids = ["qwen3.5-4b", "qwen2.5-3b"]
    assert catalog.route("привет", ids, "qwen3.5-4b") == "qwen2.5-3b"
    assert catalog.route("который час?", ids, "qwen3.5-4b") == "qwen2.5-3b"


def test_unknown_preferred_falls_back_to_catalog_head():
    ids = ["qwen3.5-4b", "qwen2.5-3b"]
    assert catalog.route("объясни кэш", ids, "нет такой") == "qwen3.5-4b"


if __name__ == "__main__":
    for n, fn in sorted(list(globals().items())):
        if n.startswith("test_") and callable(fn):
            fn()
            print("OK", n)
    print("ALL OK model router")
