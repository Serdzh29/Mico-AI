"""Первый этап: общий каталог действий (web_search), поле сообщения в мессенджере. Без Windows и сети."""
import os as _os, sys as _sys, types as _types
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
from win import agent
from win import messenger
from win import osagent
from web import find as webfind


def test_model_can_choose_web_search_for_free_phrasing():
    assert osagent.wants_action("найди в интернете рецепт борща")
    assert osagent.wants_action("поищи в гугле погоду в Берлине")
    assert not osagent.wants_action("что такое интернет")
    name, args = osagent.parse('{"action": "web_search", "args": {"query": "рецепт борща", "open_first": false}}')
    assert name == "web_search" and args == {"query": "рецепт борща", "open_first": False}


def test_web_search_is_safe_and_grounded():
    assert not osagent.needs_confirm("web_search")                 # открыть поиск — без «да»
    args = {"query": "рецепт борща", "open_first": False}
    assert osagent.grounded("web_search", args, "найди в интернете рецепт борща")
    assert not osagent.grounded("web_search", args, "расскажи про интернет")   # без глагола поиска — не выполняем


def test_web_search_has_description_and_undo_note():
    assert "поиск" in osagent.describe("web_search", {"query": "x", "open_first": True})
    assert osagent.UNDO_NOTE["web_search"]


def test_execute_web_search_starts_background_search(monkeypatch=None):
    # execute() импортирует commands, actions и winctl — подставляем пустые модули, чтобы проверить только ветку поиска
    for mod in ("commands", "actions", "winctl"):
        _sys.modules.setdefault(mod, _types.ModuleType(mod))
    started = []
    real_start = webfind.start
    webfind.start = lambda spec, click, notify: started.append(spec)
    try:
        text = osagent.execute("web_search", {"query": "  рецепт   борща ", "open_first": True})
    finally:
        webfind.start = real_start
    assert started == [{"kind": "google", "query": "рецепт борща", "open_first": True}]
    assert "борща" in text


def test_message_field_by_name():
    assert messenger.find_message_field(["Поиск", "Введите сообщение"]) == "Введите сообщение"
    assert messenger.find_message_field(["Поиск", "Search messages"]) is None
    assert messenger.find_message_field([]) is None


class Driver:
    def __init__(self, buttons, fields):
        self.buttons, self.fields, self.calls = buttons, fields, []

    def snapshot(self):
        return {"title": "Telegram", "buttons": self.buttons, "fields": self.fields, "password": False}

    def do(self, name, args):
        self.calls.append((name, args))
        return True, ""


def test_send_uses_named_message_field():
    drv = Driver(["Алексей"], ["Поиск", "Введите сообщение"])
    text = agent.Runner("открой телеграм и напиши алексею привет", lambda p: "", drv,
                        lambda q: True, lambda t: None).run()
    assert text.startswith("Отправил")
    assert (agent.FILL, {"field": "Введите сообщение", "text": "привет"}) in drv.calls
    assert not any(c[0] == agent.TYPE and c[1].get("text") == "привет" for c in drv.calls)   # текст не в фокус


def test_send_falls_back_to_typing_without_field():
    drv = Driver(["Алексей"], ["Поиск"])
    agent.Runner("открой телеграм и напиши алексею привет", lambda p: "", drv,
                 lambda q: True, lambda t: None).run()
    assert (agent.TYPE, {"text": "привет"}) in drv.calls


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("test_stage1: все проверки прошли")
