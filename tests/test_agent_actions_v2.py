"""Действия агента: вкладки, страницы, окна, полный экран и музыка. Чистая логика и маршрут команд, без Windows.
Запуск: python tests/test_agent_actions_v2.py"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import stubs_for_tests   # noqa: E402  подменяет модули Windows на время проверок
stubs_for_tests.install()

from unittest import mock  # noqa: E402
from win import osagent as O   # noqa: E402
from core import typo   # noqa: E402
from ui import widgets as components   # noqa: E402


def test_new_actions_parse_from_model_json():
    assert O.parse('{"action": "fullscreen", "args": {"on": false}}') == ("fullscreen", {"on": False})
    assert O.parse('{"action": "media", "args": {"command": "stop"}}') == ("media", {"command": "stop"})
    assert O.parse('{"action": "window_state", "args": {"state": "свернуть"}}') == ("window_state", {"state": "minimize"})
    assert O.parse('{"action": "new_tab"}') == ("new_tab", {})
    assert O.parse('{"action": "open_url", "args": {"url": "apple.com"}}') == ("open_url", {"url": "apple.com"})
    assert O.parse('{"media": "next"}') == ("media", {"command": "next"}), "короткая форма от маленькой модели"


def test_bool_words_are_accepted_and_nonsense_is_refused():
    assert O.parse('{"action": "fullscreen", "args": {"on": "нет"}}')[1] == {"on": False}
    assert O.parse('{"action": "fullscreen", "args": {"on": "true"}}')[1] == {"on": True}
    for bad in ('{"action": "fullscreen", "args": {"on": "может быть"}}',
                '{"action": "media", "args": {"command": "format"}}',
                '{"action": "window_state", "args": {"state": "закопать"}}'):
        try:
            O.parse(bad)
        except ValueError:
            continue
        raise AssertionError("должно быть отказом: " + bad)


def test_new_actions_run_without_confirmation_like_opening():
    for name in ("open_url", "new_tab", "focus_window", "window_state", "fullscreen", "media"):
        assert not O.needs_confirm(name), name
    assert O.needs_confirm("set_volume"), "изменения настроек по-прежнему с «да»"


def test_grounding_needs_a_command_not_a_question():
    cases = [
        ("выйди из полноэкранного режима", "fullscreen", {"on": False}, True),
        ("выйди из полноэкранного режима", "fullscreen", {"on": True}, False),
        ("включи полноэкранный режим", "fullscreen", {"on": True}, True),
        ("видео на весь экран", "fullscreen", {"on": True}, True),
        ("что такое полноэкранный режим?", "fullscreen", {"on": True}, False),
        ("открой новую вкладку", "new_tab", {}, True),
        ("что такое вкладка?", "new_tab", {}, False),
        ("открой ютуб", "open_url", {"url": "ютуб"}, True),
        ("что такое сайт?", "open_url", {"url": "сайт"}, False),
        ("переключись на телеграм", "focus_window", {"title": "телеграм"}, True),
        ("сверни окно", "window_state", {"state": "minimize"}, True),
        ("останови музыку", "media", {"command": "play_pause"}, True),
        ("следующий трек", "media", {"command": "next"}, True),
        ("расскажи про музыку, какая лучшая?", "media", {"command": "play_pause"}, False),
    ]
    wrong = [c for c in cases if O.grounded(c[1], c[2], c[0]) != c[3]]
    assert not wrong, wrong


def test_chat_questions_do_not_show_the_action_list_to_the_model():
    """Иначе обычный вопрос про музыку или сайт получит JSON вместо ответа."""
    for q in ("какая твоя любимая музыка?", "что такое сайт?", "посоветуй фильм на вечер", "расскажи про видео"):
        assert not O.wants_action(q), q
    for q in ("выйди из полноэкранного режима", "открой новую вкладку", "останови музыку", "сверни окно"):
        assert O.wants_action(q), q


def test_fullscreen_undo_is_exact_and_others_say_why():
    assert O.inverse("fullscreen", {"on": True}) == ("fullscreen", {"on": False})
    assert O.inverse("fullscreen", {"on": False}) == ("fullscreen", {"on": True})
    for name in ("open_url", "new_tab", "media", "focus_window", "window_state"):
        assert O.UNDO_NOTE[name], name


def test_describe_is_human_readable():
    assert O.describe("fullscreen", {"on": False}) == "выйти из полноэкранного режима"
    assert O.describe("media", {"command": "next"}) == "следующий трек"
    assert O.describe("window_state", {"state": "maximize"}) == "развернуть окно"


def test_execute_maps_to_the_right_windows_calls():
    from win import system as W
    calls = []
    saved = {k: getattr(W, k) for k in ("press", "set_fullscreen", "new_tab", "show_window", "open_url")}
    W.press = lambda *a, **k: calls.append(("press", a))
    W.set_fullscreen = lambda h, on: (calls.append(("fs", h, on)), (True, "готово"))[1]
    W.new_tab = lambda h: (calls.append(("tab", h)), (True, "Открыл новую вкладку."))[1]
    W.show_window = lambda h, cmd: calls.append(("show", h, cmd))
    W.open_url = lambda url: calls.append(("url", url))
    try:
        assert O.execute("media", {"command": "stop"}, lambda t: None, lambda: 5) == "Готово."
        assert O.execute("fullscreen", {"on": False}, lambda t: None, lambda: 5) == "готово"
        assert O.execute("new_tab", {}, lambda t: None, lambda: 5) == "Открыл новую вкладку."
        assert O.execute("window_state", {"state": "restore"}, lambda t: None, lambda: 5) == "Готово."
        assert O.execute("open_url", {"url": "apple.com"}, lambda t: None, lambda: 5) == "Открыл страницу."
        assert O.execute("open_url", {"url": "неизвестный сайт"}, lambda t: None, lambda: 5).startswith("Не понял адрес")
    finally:
        for k, v in saved.items():
            setattr(W, k, v)
    assert ("press", ("stop",)) in calls and ("fs", 5, False) in calls and ("tab", 5) in calls
    assert ("show", 5, 9) in calls and ("url", "https://apple.com") in calls
    assert not any(c[0] == "url" and "неизвестный" in str(c) for c in calls), "неизвестный адрес не открываем"


def test_stop_music_is_not_mistyped_into_install():
    """Было: «останови музыку» исправлялась на «установи» и открывала музыку в браузере."""
    c = typo.Corrector(None, {w for t in components.TOGGLES for k in t.keys for w in k.split() if len(w) >= 4})
    for q in ("останови музыку", "выйди из полноэкранного режима", "открой новую вкладку", "верни окно", "пауза"):
        fixed, changes = c.correct(q)
        assert fixed == q and not changes, (q, fixed, changes)


def test_media_and_window_commands_route_to_windows_helpers():
    from win import commands
    from win import system as W
    calls = []
    saved = {k: getattr(W, k) for k in ("press", "set_fullscreen", "new_tab")}
    W.press = lambda *a, **k: calls.append(("press", a))
    W.set_fullscreen = lambda h, on: (calls.append(("fs", h, on)), (True, "ok"))[1]
    W.new_tab = lambda h: (calls.append(("tab", h)), (True, "ok"))[1]
    try:
        commands.handle("останови музыку", lambda t: None, lambda: 9)
        commands.handle("выйди из полноэкранного режима", lambda t: None, lambda: 9)
        commands.handle("на весь экран", lambda t: None, lambda: 9)
        commands.handle("открой новую вкладку", lambda t: None, lambda: 9)
    finally:
        for k, v in saved.items():
            setattr(W, k, v)
    assert ("press", ("play",)) in calls, calls
    assert ("fs", 9, False) in calls and ("fs", 9, True) in calls, calls
    assert ("tab", 9) in calls, calls


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("OK agent actions v2")
