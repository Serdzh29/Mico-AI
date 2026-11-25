"""Мессенджеры: разбор фразы, имя контакта в нужном падеже, поиск чата в списке, порядок действий. Без Windows."""
import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
from win import agent
from win import messenger as M


def test_parse_takes_name_and_text_apart():
    t = M.parse("открой телеграм и напиши алексею привет")
    assert (t["app"], t["who"], t["text"]) == ("телеграм", "алексею", "привет")
    # имя пишем полным в именительном падеже: обрезанное «алексе» поиск не находил
    assert t["candidates"][0] == "алексей" and t["search"] == "алексей"


def test_parse_keeps_text_with_punctuation_and_colon():
    t = M.parse("открой MAX и напиши мамуле: как дела?")
    assert t["app"] == "MAX" and t["who"] == "мамуле" and t["text"] == "как дела?"
    # «мамуле» → «мамуля» (как подписывают близких), «мама» — запасной вариант дальше
    assert t["candidates"][0] == "мамуля" and "мама" in t["candidates"]


def test_parse_ignores_other_programs_and_phrases():
    assert M.parse("открой блокнот и напиши привет") is None      # не мессенджер
    assert M.parse("открой телеграм") is None                      # нет адресата и текста
    assert M.parse("открой телеграм и напиши алексею") is None


def test_declension_variants():
    assert "алексей" in M.candidates("алексею")
    assert "саша" in M.candidates("саше") and "саша" in M.candidates("сашу")
    assert "катя" in M.candidates("кате")
    assert "алексей" in M.candidates("алексеем")


def test_match_contact_finds_name_from_dative():
    names = ["Чат AppleInsider.ru", "Алексей", "Lpr 1"]
    assert M.match_contact(M.candidates("алексею"), names) == "Алексей"


def test_match_contact_prefers_chat_title_over_message_snippet():
    names = ["Алексей алексей привет", "Алексей"]
    assert M.match_contact(M.candidates("алексею"), names) == "Алексей"


def test_match_contact_handles_emoji_and_kin():
    assert M.match_contact(M.candidates("мамуле"), ["Папа", "Мама ❤️"]) == "Мама ❤️"


def test_match_contact_prefers_full_nickname_form():
    # контакт подписан «Мамуля» — его и находим, а не «Мама»
    assert M.match_contact(M.candidates("мамуле"), ["Мамуля"]) == "Мамуля"


def test_match_contact_returns_none_when_absent():
    assert M.match_contact(M.candidates("борису"), ["Алексей", "Lpr 1"]) is None


class FakeDriver:
    """Вместо Windows: список чатов и журнал нажатий."""
    def __init__(self, buttons):
        self.buttons, self.calls = buttons, []

    def snapshot(self):
        return {"title": "Telegram", "buttons": list(self.buttons), "fields": [], "password": False}

    def do(self, name, args):
        self.calls.append((name, args.get("name") or args.get("text") or args.get("key") or args.get("sec")))
        return True, ""


def _run(goal, buttons, answer):
    drv, said = FakeDriver(buttons), []
    r = agent.Runner(goal, lambda p: "", drv, lambda q: said.append(q) or answer, lambda t: None)
    return r.run(), drv, said


def test_send_flow_asks_then_types_and_presses_enter():
    text, drv, said = _run("открой телеграм и напиши алексею привет", ["Чат AppleInsider.ru", "Алексей"], True)
    names = [c[0] for c in drv.calls]
    assert names[:3] == [agent.LAUNCH, agent.WAIT, agent.PRESS]
    assert ("Алексей" in [c[1] for c in drv.calls])                 # открыт чат «Алексей»
    assert said and "Алексей" in said[0] and "привет" in said[0]
    assert drv.calls[-2:] == [(agent.TYPE, "привет"), (agent.PRESS, "enter")]
    assert text.startswith("Отправил")


def test_no_send_when_user_says_no():
    text, drv, _ = _run("открой телеграм и напиши алексею привет", ["Алексей"], False)
    assert text == "Хорошо, не отправляю."
    assert (agent.TYPE, "привет") not in drv.calls


class ListDriver(FakeDriver):
    """Окно, которое показывает результаты поиска через UI Automation: после ввода имени в списке появляются чаты."""
    def __init__(self, buttons, results):
        super().__init__(buttons)
        self.results, self.typed = results, False

    def snapshot(self):
        snap = super().snapshot()
        if self.typed:
            snap["buttons"] = list(self.buttons) + list(self.results)
        return snap

    def do(self, name, args):
        if name == agent.TYPE:
            self.typed = True
        return super().do(name, args)


def test_unknown_contact_in_readable_list_stops_without_sending():
    drv, said = ListDriver(["Настройки"], ["Алексей", "Чат работы"]), []
    r = agent.Runner("открой телеграм и напиши борису привет", lambda p: "", drv, lambda q: said.append(q) or True, lambda t: None)
    text = r.run()
    assert "не нашёл контакт" in text
    assert not any(c[0] == agent.PRESS and c[1] == "enter" for c in drv.calls)
    assert not said, "контакта нет в видимом списке — ничего не спрашиваем и не отправляем"


def test_blind_search_types_one_name_and_asks_to_check_screen():
    """Telegram и MAX не отдают список чатов через UI Automation: агент не гадает варианты имени одно за другим
    (раньше «мамуля» превращалась в «мамулямамула»), а вводит имя один раз, открывает верхний результат и просит проверить чат."""
    text, drv, said = _run("открой телеграм и напиши мамуле привет", ["Настройки"], True)
    typed = [c[1] for c in drv.calls if c[0] == agent.TYPE]
    assert typed[0] == "мамуля" and "мамула" not in typed, typed       # одно имя, без перебора вариантов
    assert any(c == (agent.PRESS, "backspace") for c in drv.calls)      # старый текст в поиске стирается
    assert said and "Проверь на экране" in said[0] and "привет" in said[0]
    assert text.startswith("Отправил")


def test_blind_search_no_send_when_user_says_no():
    text, drv, said = _run("открой телеграм и напиши мамуле привет", ["Настройки"], False)
    assert text == "Хорошо, не отправляю."
    assert (agent.TYPE, "привет") not in drv.calls


def test_whatsapp_picks_result_with_arrow_then_enter():
    assert M.pick_keys("whatsapp") == ("down", "enter") and M.pick_keys("телеграм") == ("enter",)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("test_messenger: все проверки прошли")
