"""Контекст чата и названия: модель помнит открытый чат, название берётся из первого запроса."""
import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
from core import title as chat_title
from core import dialog as D


def test_title_from_first_request_is_short_and_clean():
    assert chat_title.make_title("мико, как тебя зовут?") == "Как тебя зовут"
    t = chat_title.make_title("Подскажи пожалуйста, как настроить голосовой режим на Windows 11 без интернета?")
    assert t.startswith("Как настроить") and t.endswith("…") and len(t) <= chat_title.MAX_CHARS + 1


def test_title_is_built_from_question_only():
    # раньше название делала модель по ответу, и в него попадало «[thinking] Я задумался…»
    # теперь функция принимает только первый запрос пользователя
    import inspect
    assert list(inspect.signature(chat_title.make_title).parameters) == ["text"]
    assert chat_title.make_title("что такое brawl stars") == "Что такое brawl stars"


def test_title_fallback_for_empty_input():
    assert chat_title.make_title("   ") == chat_title.DEFAULT


def test_open_chat_is_not_forgotten_by_timer():
    d = D.Dialog(window=900)
    d.pinned = True                                   # открыт чат: окно по времени не действует
    d.add("user", "мой друг Саша любит шахматы", now=1000)
    d.add("mico", "Запомнил", now=1001)
    assert len(d.messages(now=1000 + 5000)) == 2      # через час открытый чат всё ещё в контексте


def test_messages_limit_keeps_latest_turns():
    d = D.Dialog(window=900, max_turns=12)
    d.pinned = True
    for i in range(10):
        d.add("user" if i % 2 == 0 else "mico", f"реплика {i}", now=1000 + i)
    last = d.messages(now=1010, limit=4)
    assert [m["content"] for m in last] == ["реплика 6", "реплика 7", "реплика 8", "реплика 9"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK chat context & titles")
