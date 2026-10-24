"""В обычном чате Mico показывает разные эмоции: радость — только с поводом, ответы выбирают эмоцию по смыслу,
модель не повторяет одно настроение без причины. Проверяется по коду и на чистых функциях emotions."""
import os as _os
import re
import sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import emotions  # noqa: E402
from actions import Reply  # noqa: E402


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_reply_mood_defaults_to_meaning_not_happy():
    check(Reply("Сейчас у тебя Windows 11").mood == "idle", "обычный ответ — спокойствие, не радость")
    check(Reply("Не получилось очистить корзину").mood == "worried", "ошибка — тревога")
    check(Reply("Записал: купить хлеб").mood == "happy", "подтверждение — радость")
    check(Reply("Что ещё сделать?").mood == "curious", "вопрос — любопытство")


def test_explicit_happy_is_no_longer_the_default_in_commands():
    cmds = read("commands.py") + read("brain.py") + read("actions.py") + read("main.py")
    left = [ln for ln in cmds.split("\n") if "Reply(" in ln and '"happy")' in ln]
    check(not left, f"явная радость осталась в ответах-командах: {left[:2]}")


def test_sad_is_not_triggered_by_everyday_words():
    check(emotions.detect_emotion("Мне плохо и устал") is None, "«плохо» и «устал» — не грусть")
    check(emotions.detect_emotion("мне грустно") == "sad", "явная грусть распознаётся")


def test_model_is_told_about_variety_and_no_default_happy():
    b = read("brain.py")
    check("не ставь [happy] только за дружелюбный тон" in b, "радость — только с поводом")
    check("def _variety_hint(self):" in b and "self._variety_hint()" in b, "модели подсказывают недавние настроения")
    check("self._recent_moods = (getattr(self, \"_recent_moods\", []) + [r.mood])[-6:]" in b,
          "последние настроения запоминаются")
    check('mood, text = split_mood((raw or "").strip())' in b and "or for_reply(text)" in b,
          "без метки — эмоция по смыслу, а не радость")


def test_variety_hint_discourages_repeats():
    import pytest
    try:
        import brain                      # на Windows импортируется; без win32 — проверка по коду выше
    except ImportError:
        pytest.skip("brain требует модули Windows")

    class Fake:
        _recent_moods = ["happy", "happy", "happy"]
    hint = brain.Brain._variety_hint(Fake())
    check("выбери другое" in hint, hint)
    Fake._recent_moods = ["happy", "sad"]
    check("Не повторяй" in brain.Brain._variety_hint(Fake()), "мягкое напоминание о разнообразии")
