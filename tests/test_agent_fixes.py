"""Исправления режима агента: имена в дательном падеже, ложные подтверждения и отказы, разбор чисел."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from win import agent, messenger


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_male_names_dative():
    check(messenger.candidates("ивану")[0] == "иван", "«ивану» → «иван»")
    check(messenger.candidates("антону")[0] == "антон", "«антону» → «антон»")
    check(messenger.candidates("алексею")[0] == "алексей", "прежние имена не сломались")
    check(messenger.candidates("мамуле")[0] == "мамуля", "«мамуле» → «мамуля»")


def test_microsoft_teams():
    check(messenger.parse("открой Microsoft Teams и напиши Ивану привет") is not None, "Microsoft Teams — мессенджер")
    check(messenger.search_hotkey("Microsoft Teams") == "ctrl+e", "в Teams поиск по Ctrl+E")


def test_cards_and_pictures_not_refused():
    check(agent.check(agent.FILL, {"field": "Поиск по картинкам", "text": "кот"}, {"title": "Яндекс"})[0] == agent.OK, "«картинки» — не карта")
    check(agent.check(agent.FILL, {"field": "Номер карты", "text": "1"}, {"title": "Магазин"})[0] == agent.REFUSE, "номер карты — отказ")
    check(agent.check(agent.FILL, {"field": "Пароль", "text": "1"}, {"title": "Вход"})[0] == agent.REFUSE, "пароль — отказ")


def test_banquet_window_not_guarded():
    check(agent.check(agent.TYPE, {"text": "привет"}, {"title": "Банкет — заметки"})[0] == agent.OK, "«Банкет» — не банк")
    check(agent.check(agent.TYPE, {"text": "1"}, {"title": "Сбербанк — личный кабинет банка"})[0] in (agent.OK, agent.REFUSE), "не падает")
    check(agent.check(agent.TYPE, {"text": "1"}, {"title": "Банк — вход"})[0] == agent.REFUSE, "окно банка защищено")


def test_price_word_not_in_percent():
    check(not agent.BUY_WORDS.search("нажму «Процент»"), "«процент» — не покупка")
    check(agent.BUY_WORDS.search("нажму «Цена»"), "«цена» — покупка")


def test_wait_number_in_text():
    name, args = agent.validate({"action": "wait", "args": {"sec": "3 секунды"}})
    check(args["sec"] == 3, "«3 секунды» → 3")


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("ok")
