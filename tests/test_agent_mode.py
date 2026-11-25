"""Режим агента (agent.py): разбор просьб и ответов модели, подтверждения перед отправкой, цикл шагов.
Без Windows и без модели: драйвер и модель подменяются. Запуск: python tests/test_agent_mode.py"""
import os, sys, threading
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from win import agent as A


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


class FakeDriver:
    """Экран, который не меняется; запоминает, что ему велели сделать."""

    def __init__(self, title="Блокнот", password=False):
        self.title, self.password = title, password
        self.done = []

    def snapshot(self):
        return {"title": self.title, "buttons": ["Отправить", "Сохранить"], "fields": ["Текст"],
                "password": self.password}

    def do(self, name, args):
        self.done.append((name, args))
        return True, ""


def script(*replies):
    """Модель, которая по очереди отдаёт заготовленные ответы."""
    queue = list(replies)

    def model(prompt):
        return queue.pop(0) if queue else '{"action": "done", "args": {"text": "конец"}}'
    return model


def act(_action, **args):
    import json
    return json.dumps({"action": _action, "args": args}, ensure_ascii=False)


# ---------- просьбы ----------
def test_request_recognises_start_stop_help():
    check(A.request("агент, открой блокнот и напиши привет") == ("start", "открой блокнот и напиши привет"))
    check(A.request("Агент: открой калькулятор") == ("start", "открой калькулятор"))
    check(A.request("стоп агент") == ("stop", None))
    check(A.request("останови агента") == ("stop", None))
    check(A.request("агент") == ("help", None))
    check(A.request("открой блокнот") is None, "обычная команда — не агент")
    check(A.request("агентство новостей") is None, "слово «агентство» — не просьба агенту")


def test_ui_task_detection_routes_open_and_act_phrases():
    check(A.is_ui_task("открой блокнот и напиши хай"))
    check(A.is_ui_task("открой телеграм и напиши мамуле привет"))
    check(A.is_ui_task("Открой Блокнот и нажми сохранить"))
    check(not A.is_ui_task("открой блокнот"), "просто открыть — обычная команда")
    check(not A.is_ui_task("напиши стих про весну"), "обычная просьба написать — не задача агента")
    check(not A.is_ui_task("открой сайт и покажи погоду"), "показать — не действие в программе")
    check(not A.is_ui_task("что такое агент"))


def test_sendkeys_escapes_special_characters():
    check(A.sendkeys_text("1+1=2") == "1{+}1=2")
    check(A.sendkeys_text("{x}") == "{{}x{}}")
    check(A.sendkeys_text("привет (мир)") == "привет {(}мир{)}")


# ---------- разбор ответа модели ----------
def test_parse_takes_action_from_prose():
    name, args = A.parse('Вот шаг: {"action": "type", "args": {"text": "привет"}} готово')
    check(name == A.TYPE and args == {"text": "привет"})


def test_parse_rejects_unknown_and_bad_args():
    for bad in ['{"action": "rm_rf", "args": {}}', '{"action": "type", "args": {"text": ""}}',
                '{"action": "press", "args": {"key": "f12"}}', "просто текст без действия",
                '{"action": "launch", "args": {}}', '{"action": "fill", "args": {"field": "Поле"}}']:
        try:
            A.parse(bad)
        except ValueError:
            continue
        raise AssertionError(f"должно быть отказом: {bad}")


def test_parse_clamps_wait_and_lowercases_keys():
    check(A.parse('{"action": "wait", "args": {"sec": 99}}')[1] == {"sec": 5})
    check(A.parse('{"action": "press", "args": {"key": "ENTER"}}')[1] == {"key": "enter"})


# ---------- риск: что нужно подтвердить ----------
def test_send_like_buttons_need_confirmation():
    snap = {"title": "Почта"}
    for label in ("Отправить", "Send", "Опубликовать", "Оплатить", "Удалить", "Подтвердить"):
        verdict, _ = A.check(A.CLICK, {"name": label}, snap)
        check(verdict == A.CONFIRM, f"«{label}» должно спрашивать разрешение")
    verdict, _ = A.check(A.CLICK, {"name": "Сохранить"}, snap)
    check(verdict == A.OK, "обычная кнопка — без вопроса")


def test_enter_needs_confirmation_but_tab_does_not():
    check(A.check(A.PRESS, {"key": "enter"}, {"title": "Чат"})[0] == A.CONFIRM)
    check(A.check(A.PRESS, {"key": "tab"}, {"title": "Чат"})[0] == A.OK)


def test_passwords_and_guarded_windows_are_refused():
    check(A.check(A.TYPE, {"text": "1234"}, {"title": "Вход", "password": True})[0] == A.REFUSE)
    check(A.check(A.TYPE, {"text": "x"}, {"title": "KeePass — база"})[0] == A.REFUSE)
    check(A.check(A.CLICK, {"name": "Перевод"}, {"title": "Банк Онлайн"})[0] == A.REFUSE)
    check(A.check(A.TYPE, {"text": "привет"}, {"title": "Блокнот"})[0] == A.OK)


# ---------- цикл ----------
def test_confirmed_send_runs_and_is_journaled():
    drv = FakeDriver()
    asked, journal = [], []
    model = script(act("click", name="Отправить"), act("done", text="Отправил"))
    r = A.Runner("отправь письмо", model, drv, lambda q: asked.append(q) or True, lambda t: None,
                 journal=journal.append)
    result = r.run()
    check(result == "Отправил", result)
    check(asked and "Отправить" in asked[0], asked)
    check(drv.done == [(A.CLICK, {"name": "Отправить"})], drv.done)
    check(journal and "Отправить" in journal[0], journal)


def test_refused_send_stops_without_clicking():
    drv = FakeDriver()
    r = A.Runner("отправь", script(act("click", name="Отправить")), drv, lambda q: False, lambda t: None)
    result = r.run()
    check("не делаю" in result, result)
    check(drv.done == [], "без «да» кнопку не нажимаем")


def test_no_confirmation_for_plain_steps():
    drv = FakeDriver()
    asked = []
    model = script(act("launch", name="блокнот"), act("type", text="привет"), act("press", key="tab"),
                   act("done", text="готово"))
    r = A.Runner("набери текст в блокноте, а потом табом", model, drv, lambda q: asked.append(q) or True, lambda t: None)
    check(r.run() == "готово")
    check(asked == [], "открыть, ввести текст и табом — без вопросов")
    check([d[0] for d in drv.done] == [A.LAUNCH, A.TYPE, A.PRESS], drv.done)


def test_password_field_is_skipped_and_model_can_continue():
    drv = FakeDriver(password=True)
    model = script(act("type", text="секрет"), act("done", text="не стал вводить пароль"))
    r = A.Runner("войди", model, drv, lambda q: True, lambda t: None)
    check(r.run() == "не стал вводить пароль")
    check(drv.done == [], "в поле пароля ничего не вводим")


def test_garbage_replies_stop_the_run():
    r = A.Runner("что-то", script("мм", "не знаю", "эээ"), FakeDriver(), lambda q: True, lambda t: None)
    check("остановился" in r.run())


def test_step_limit_stops_the_run():
    model = script(*[act("wait", sec=1)] * 5)
    r = A.Runner("долго", model, FakeDriver(), lambda q: True, lambda t: None, max_steps=3)
    check("3 шагов" in r.run())


def test_stop_request_is_honoured():
    r = A.Runner("любая задача", script(act("wait", sec=1)), FakeDriver(), lambda q: True, lambda t: None)
    r.stop()
    check("Остановил" in r.run())


def test_errors_are_reported_not_raised():
    class Broken(FakeDriver):
        def snapshot(self):
            raise RuntimeError("UIA недоступна")
    got = []
    r = A.Runner("задача", script(), Broken(), lambda q: True, got.append)
    r.running = True
    r._run_safe()
    check(got and "UIA недоступна" in got[0], got)
    check(r.running is False)


def test_each_step_is_announced_and_logged():
    said, logged = [], []
    model = script(act("launch", name="телеграм"), act("type", text="привет"), act("done", text="готово"))
    r = A.Runner("задача", model, FakeDriver(), lambda q: True, said.append, log=logged.append)
    check(r.run() == "готово")
    check("Агент: открываю «телеграм»" in said and "Агент: ввожу текст «привет»" in said, said)
    check(said.count("Агент думает над следующим шагом…") == 3, said)
    check(any("шаг launch" in x for x in logged), logged)


def test_fill_and_key_combos_parse_and_map():
    name, args = A.parse('{"action": "fill", "args": {"field": "Адрес", "text": "example.com"}}')
    check(name == A.FILL and args == {"field": "Адрес", "text": "example.com"}, args)
    check(A.parse('{"action": "press", "args": {"key": "Ctrl+L"}}')[1] == {"key": "ctrl+l"})
    check(A.KEY_MAP["ctrl+l"] == "^l" and A.KEY_MAP["pagedown"] == "{PGDN}")
    try:
        A.parse('{"action": "press", "args": {"key": "alt+f4"}}')
    except ValueError:
        pass
    else:
        raise AssertionError("alt+f4 не разрешаем: это закрытие окна без подтверждения")


def test_risky_key_and_field_rules():
    check(A.check(A.PRESS, {"key": "ctrl+w"}, {"title": "Chrome"})[0] == A.CONFIRM, "Ctrl+W закрывает вкладку")
    check(A.check(A.PRESS, {"key": "ctrl+l"}, {"title": "Chrome"})[0] == A.OK)
    check(A.check(A.FILL, {"field": "Пароль", "text": "x"}, {"title": "Сайт"})[0] == A.REFUSE)
    check(A.check(A.FILL, {"field": "Номер карты", "text": "1"}, {"title": "Магазин"})[0] == A.REFUSE)
    check(A.check(A.FILL, {"field": "Поиск", "text": "погода"}, {"title": "Chrome"})[0] == A.OK)
    check(A.check(A.FILL, {"field": "Почта", "text": "x"}, {"title": "Банк онлайн"})[0] == A.REFUSE)


def test_browser_and_no_element_hints_in_prompt():
    p = A.prompt("открой сайт", [], {"title": "Новая вкладка — Google Chrome", "buttons": [], "fields": []})
    check("ctrl+l" in p and "Это браузер" in p)
    p2 = A.prompt("играй", [], {"title": "Elden Ring", "buttons": [], "fields": []})
    check("честно скажи" in p2 and "Это браузер" not in p2)


def test_model_gets_short_token_budget():
    check(A.MODEL_TOKENS <= 300, "для одного шага хватит короткого JSON")


def test_prompt_contains_goal_and_screen():
    p = A.prompt("открой калькулятор", ["launch → ок"], {"title": "Рабочий стол", "buttons": ["Пуск"], "fields": []})
    check("открой калькулятор" in p and "Рабочий стол" in p and "Пуск" in p and "launch → ок" in p)


def test_request_keeps_case_of_goal():
    check(A.request("Агент, открой Блокнот и напиши Привет") == ("start", "открой Блокнот и напиши Привет"))


def test_model_names_and_args_are_forgiven():
    name, args = A.parse('{"action": "open_app", "args": {"app": "Блокнот"}}')
    check(name == A.LAUNCH and args == {"name": "Блокнот"}, args)
    name, args = A.parse('{"action": "write", "args": {"value": "привет"}}')
    check(name == A.TYPE and args == {"text": "привет"}, args)
    check(A.parse('{"action": "launch", "args": "блокнот"}')[1] == {"name": "блокнот"})
    check(A.parse('{"action": "type", "text": "хай"}')[1] == {"text": "хай"})
    check(A.parse('{"action": "press", "args": {"key": "Return"}}')[1] == {"key": "enter"})
    check(A.parse('{"action": "открыть", "args": {"name": "калькулятор"}}')[0] == A.LAUNCH)


def test_bad_first_object_does_not_hide_good_one():
    name, _ = A.parse('{"action": "rm_rf"} а вот {"action": "done", "args": {"text": "ок"}}')
    check(name == A.DONE)


def test_simple_plan_runs_without_model():
    drv = FakeDriver()

    def model(prompt):
        raise AssertionError("для простой задачи модель не нужна")
    r = A.Runner("Открой Блокнот и напиши Привет", model, drv, lambda q: True, lambda t: None)
    result = r.run()
    check(result == "Открыл «Блокнот» и ввёл текст.", result)
    check([d[0] for d in drv.done] == [A.LAUNCH, A.WAIT, A.TYPE], drv.done)
    check(drv.done[2][1] == {"text": "Привет"}, drv.done)


def test_plan_failure_gives_model_a_correction():
    """Самокоррекция: план споткнулся — модель получает ошибку шага и придумывает другой путь.
    Если модель не может — агент честно останавливается и ничего лишнего не делает."""
    class NoLaunch(FakeDriver):
        def do(self, name, args):
            self.done.append((name, args))
            return name != A.LAUNCH, "не нашёл программу"
    prompts = []
    answers = ['{"action": "type", "args": {"text": "привет"}}',
               '{"action": "done", "args": {"text": "Готово: ввёл текст другим путём."}}']

    def correcting(prompt):
        prompts.append(prompt)
        return answers.pop(0) if answers else '{"action": "done", "args": {"text": "Готово."}}'

    drv = NoLaunch()
    result = A.Runner("открой фотошоп и напиши привет", correcting, drv, lambda q: True, lambda t: None).run()
    check("не вышло" in " ".join(prompts), "модель видит ошибку шага")
    check(result == "Готово: ввёл текст другим путём." and [d[0] for d in drv.done] == [A.LAUNCH, A.TYPE],
          (result, drv.done))

    # модель молчит — агент останавливается честно и не творит лишнего
    drv2 = NoLaunch()
    result2 = A.Runner("открой фотошоп и напиши привет", lambda p: "", drv2, lambda q: True, lambda t: None).run()
    check(("Не смог понять" in result2 or "Не получилось" in result2) and len(drv2.done) == 1,
          (result2, drv2.done))


def test_plan_is_not_used_for_other_tasks():
    check(A.simple_plan("напиши стих про весну") is None)
    check(A.simple_plan("открой блокнот") is None)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK agent_mode")
