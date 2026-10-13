"""Переформулировки: «погромче», «врубай вайфай», «засеки 10 минут». Главное — не перепутать действия:
«выключи» никогда не становится «включи», вопросы и отрицания не выполняются."""
import os, sys, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import intent as I

# (что написал человек, что должно получиться)
SHOULD = [
    ("погромче", "громче"),
    ("прибавь звук", "громче"),
    ("потише", "тише"),
    ("убавь громкость", None),                 # нет такого варианта — не угадываем, пусть разберутся правила
    ("врубай вайфай", "включи wi-fi"),
    ("отруби интернет", "выключи wi-fi"),
    ("засеки 10 минут", "поставь таймер на 10 минут"),
    ("сфоткай экран", "сделай скриншот"),
    ("зайди на ютуб", "открой сайт youtube.com"),
    ("сделай тёмную тему", "включи тёмную тему"),
    ("сделай громче пожалуйста", "громче"),
    ("увеличь яркость", "ярче"),
    ("откр блокнот", "открой блокнот"),
    ("громкость 30", "громкость 30"),         # числа переносятся
    ("яркость 70", "яркость 70"),
]

# Главное правило: эти пары никогда не должны меняться местами
NEVER_SWAP = [
    ("выключи звук", "включи звук"),
    ("выключи блютуз", "включи блютуз"),
    ("закрой блокнот", "открой блокнот"),
    ("отключи wi-fi", "включи wi-fi"),
    ("тише", "громче"),
    ("темнее", "ярче"),
]


def test_paraphrases_map_to_known_commands():
    for q, want in SHOULD:
        got = I.match(q)
        if want is None:
            assert got is None or got == q, (q, got)
        else:
            assert got == want, (q, got, want)


def test_opposites_are_never_swapped():
    for q, bad in NEVER_SWAP:
        got = I.match(q)
        assert got != bad, (q, got)


def test_questions_negations_and_unrelated_are_left_alone():
    for q in ["как включить wi-fi", "почему не работает блютуз", "не выключай звук", "нельзя закрыть",
              "удали все файлы", "расскажи анекдот", "сделай кофе", "что такое гибернация",
              "включи будильник", "выключи компьютер"]:
        assert I.match(q) is None, (q, I.match(q))


def test_numbers_are_carried_over_and_must_match():
    assert I.match("засеки 25 минут") == "поставь таймер на 25 минут"
    assert I.match("громкость 15") == "громкость 15"


def test_short_or_empty_input_is_ignored():
    assert I.match("") is None and I.match("ок") is None and I.match(None) is None


def test_each_canonical_phrase_is_understood_by_rules():
    """Если каноническая фраза не понимается правилами, переформулировка уйдёт в пустоту."""
    import test_capabilities as TC
    TC._stub_windows()
    import commands
    commands.os.startfile = lambda *a, **k: None
    commands.subprocess.Popen = lambda *a, **k: None
    commands.subprocess.run = lambda *a, **k: types.SimpleNamespace(returncode=0, stdout="", stderr="")
    brain_only = {"что я делал вчера", "о чём мы говорили вчера?", "что такое гибернация",
                  "что у меня на экране?", "сделай скриншот", "помодоро", "какая у меня версия Windows"}
    unhandled = []
    for canon, filled in I.all_canonical():
        if canon in brain_only:
            continue
        try:
            r = commands.handle(filled, lambda t: None, lambda: None)
        except Exception:
            r = None
        if r is None:
            unhandled.append(canon)
    assert not unhandled, unhandled


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("OK test_intent")
