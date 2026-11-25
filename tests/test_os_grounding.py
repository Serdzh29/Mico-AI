import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
from win import osagent as O
from core import phrase


def test_small_talk_never_gets_action_prompt():
    assert not O.wants_action("как дела")
    assert not O.wants_action("расскажи анекдот")
    assert O.wants_action("закрой блокнот")


def test_close_window_needs_matching_words_in_request():
    # модель выдумала окно на обычный вопрос — не выполняем
    assert not O.grounded("close_window", {"title": "След трек"}, "как дела")
    assert O.grounded("close_window", {"title": "След трек"}, "закрой след трек")


def test_other_actions_need_their_verbs():
    assert not O.grounded("set_volume", {"percent": 30}, "как дела")
    assert O.grounded("set_volume", {"percent": 30}, "громкость 30")
    assert O.grounded("open_app", {"name": "блокнот"}, "открой блокнот")


def test_abbreviations_expand_to_known_forms():
    assert phrase.canonical("выключи пк") == "выключи компьютер"
    assert phrase.canonical("закр блокнот") == "закрой блокнот"
    assert phrase.canonical("щас громк 30") == "сейчас громкость 30"
    assert phrase.canonical("как дела") == "как дела"


def test_abbreviation_only_whole_words():
    # «комплект» не должен превратиться в «компьютеров»
    assert phrase.canonical("купи комплект") == "купи комплект"
