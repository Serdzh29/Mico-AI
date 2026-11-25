"""Повтор вызова действия: битый JSON от модели чинится один раз с объяснением причины.
Проверяется поведение протокола — parse/repair, а не строки исходников."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from win import osagent


def test_parse_full_and_compact_json():
    assert osagent.parse('{"action": "set_volume", "args": {"percent": 30}}') == ("set_volume", {"percent": 30})
    assert osagent.parse('{"set_brightness": 50}') == ("set_brightness", {"percent": 50})


def test_parse_returns_none_for_plain_text():
    assert osagent.parse("Привет! Как дела?") is None
    assert osagent.parse("") is None


def test_invalid_call_raises_for_repair():
    try:
        osagent.parse('{"action": "set_volume", "args": {"громкость": 30}}')
    except ValueError as e:
        assert "percent" in str(e), "причина отказа называет правильный аргумент"
    else:
        assert False, "неправильные аргументы должны ругаться — по ним модель чинит JSON"


def test_looks_like_call_detects_failed_attempts():
    assert osagent.looks_like_call('{"action": "set_vol", ...')
    assert osagent.looks_like_call('{"set_volume": "громко"}')
    assert not osagent.looks_like_call("Включи музыку и расслабься")


def test_repair_prompt_explains_the_reason():
    p = osagent.repair_prompt('{"action": "set_volume", "args": {}}', "нет аргумента level")
    assert "нет аргумента level" in p and "action" in p, "модель получает причину и прежний ответ"


def test_repaired_call_parses():
    # модель исправилась — повторный разбор проходит
    fixed = '{"action": "set_volume", "args": {"percent": 30}}'
    assert osagent.parse(fixed) == ("set_volume", {"percent": 30})


if __name__ == "__main__":
    for n, fn in sorted(list(globals().items())):
        if n.startswith("test_") and callable(fn):
            fn()
            print("OK", n)
    print("ALL OK json call repair")
