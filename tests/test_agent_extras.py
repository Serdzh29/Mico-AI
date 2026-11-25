"""Умный агент: двойное подтверждение покупок, макросы, отчёт по шагам, отмена,
умные поля из профиля и повтор несработавших шагов. Поведение, а не строки кода.
Без Windows и без модели: драйвер и модель подменяются (как в test_agent_mode)."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from win import agent as A
from core import macro as MACRO


class FakeDriver:
    """Окно с кнопками и полями: шаги записываются, результат настраивается."""

    def __init__(self, fail_first=0, fail_names=()):
        self.done = []
        self.fail_first = fail_first              # сколько первых кликов провалить
        self.fail_names = set(fail_names)
        self.title = "Магазин — Chrome"

    def snapshot(self):
        return {"title": self.title, "buttons": ["Оплатить 1 200 ₽", "Нравится", "В корзину"],
                "fields": ["Имя", "Телефон"], "password": False}

    def do(self, name, args):
        if name == A.WAIT:
            return True, ""
        self.done.append((name, args))
        if name == A.CLICK and args.get("name") in self.fail_names and self.fail_first > 0:
            self.fail_first -= 1
            return False, "такой кнопки нет в окне"
        return True, ""


def make_runner(goal, answers, drv=None, asks=None, notifies=None):
    drv = drv or FakeDriver()
    asks = asks if asks is not None else []
    notifies = notifies if notifies is not None else []

    def model(prompt):
        return answers.pop(0) if answers else '{"action": "done", "args": {"text": "Готово."}}'

    def ask(q):
        asks.append(q)
        return True

    r = A.Runner(goal, model, drv, ask, notifies.append)
    return r, drv, asks, notifies


DONE = '{"action": "done", "args": {"text": "Готово."}}'


# ---------- 1. покупки и бронирование ----------
def test_deal_extraction_finds_price_and_date():
    deal = A.extract_deal(["нажму «Оплатить 1 200 ₽» в окне", "Бронь на завтра"])
    assert deal["price"] == "1 200 ₽", deal
    assert deal["date"] == "завтра", deal


def test_buy_needs_double_confirmation_with_price():
    answers = ['{"action": "click", "args": {"name": "Оплатить 1 200 ₽"}}', DONE]
    r, drv, asks, _ = make_runner("закажи билет", answers)
    result = r.run()
    assert result == "Готово.", result
    assert len(asks) == 2, asks
    assert "1 200 ₽" in asks[0] and ("покупка" in asks[0] or "бронирование" in asks[0]), asks[0]
    assert "Последняя проверка" in asks[1], asks[1]


def test_ordinary_step_asks_once():
    answers = ['{"action": "click", "args": {"name": "Отправить"}}', DONE]
    r, drv, asks, _ = make_runner("открой магазин", answers)
    r.run()
    assert len(asks) == 1 and "Продолжить" in asks[0], asks


def test_no_means_stop_on_deal():
    answers = ['{"action": "click", "args": {"name": "Оплатить 1 200 ₽"}}', DONE]

    def ask_no(q):
        return False
    r = A.Runner("закажи билет", lambda p: answers.pop(0), FakeDriver(), ask_no, lambda t: None)
    assert "не делаю" in r.run()


# ---------- 2. макросы ----------
def test_macro_save_and_run():
    got = MACRO.parse_save("Запомни цепочку утро: погода; открой почту; включи плейлист")
    assert got["name"] == "утро" and got["steps"] == ["погода", "открой почту", "включи плейлист"], got
    cfg = {}
    MACRO.add(cfg, got["name"], got["steps"])
    assert MACRO.get(cfg, "утро") == got["steps"]
    assert MACRO.parse_run("макрос утро") == "утро"
    assert MACRO.parse_run("выполни цепочку утро") == "утро"
    text = MACRO.describe("утро", got["steps"])
    assert "Запомнил цепочку" in text and "макрос утро" in text


def test_macro_rejects_single_and_huge_chains():
    assert MACRO.parse_save("Запомни цепочку x: одно действие") is None, "одна команда — не цепочка"
    assert MACRO.parse_save("Запомни цепочку x: " + "; ".join(f"шаг{i}" for i in range(12))) is None


def test_macro_run_needs_existing_name():
    assert MACRO.parse_run("запусти блокнот") is None, "обычные команды — не макросы"
    assert MACRO.get({}, "утро") is None


# ---------- 4. отчёт по шагам и отмена ----------
def test_report_lists_done_steps():
    answers = ['{"action": "click", "args": {"name": "Нравится"}}', DONE]
    r, drv, _asks, _n = make_runner("поставь лайк", answers)
    r.run()
    report = r.report()
    assert "Что я сделал" in report and "Нравится" in report, report
    assert len(r.done_log) == 1 and r.done_log[0][0] == A.CLICK, r.done_log   # DONE — ответ, а не шаг


def test_undo_toggles_like_but_refuses_send():
    answers = ['{"action": "click", "args": {"name": "Нравится"}}', DONE]
    r, _drv, _a, _n = make_runner("поставь лайк", answers)
    r.run()
    plan, why = r.undo_plan()
    assert plan == [(A.CLICK, {"name": "Нравится"})], (plan, why)

    answers = ['{"action": "type", "args": {"text": "привет"}}', DONE]
    r2, _drv2, _a2, _n2 = make_runner("напиши привет", answers)
    r2.run()
    plan2, why2 = r2.undo_plan()
    assert plan2 is None and "отменить нельзя" in why2, (plan2, why2)


def test_undo_without_steps_is_honest():
    r, _d, _a, _n = make_runner("пусто", [DONE])
    r.run()
    plan, why = r.undo_plan()
    assert plan is None and "ничего не делал" in why


# ---------- 5. умные поля ----------
def test_smart_fill_maps_profile_fields():
    profile = {"user_name": "Сергей", "user_phone": "+7 900 000-00-00", "user_email": "a@b.ru"}
    assert A.smart_fill("Имя", profile) == "Сергей"
    assert A.smart_fill("Телефон", profile) == "+7 900 000-00-00"
    assert A.smart_fill("Email", profile) == "a@b.ru"
    assert A.smart_fill("Имя", {"user_name": ""}) is None, "пустой профиль — не подставляем"
    assert A.smart_fill("Пароль", profile) is None and A.smart_fill("Карта", profile) is None


def test_empty_profile_field_waits_for_yes_and_can_be_skipped():
    answers = ['{"action": "fill", "args": {"field": "Имя", "text": "-"}}',
               '{"action": "fill", "args": {"field": "Имя", "text": "Сергей"}}', DONE]
    asks = []
    r = A.Runner("заполни форму", lambda p: answers.pop(0), FakeDriver(),
                 lambda q: asks.append(q) or False, lambda t: None,
                 profile={"user_name": "Сергей"})
    out = r.run()
    assert any("Сергей" in q for q in asks), asks      # спросили про подстановку
    assert "Готово" in out, out


# ---------- 6. повтор несработавших шагов ----------
def test_failed_click_is_retried_once():
    drv = FakeDriver(fail_first=1, fail_names={"В корзину"})
    answers = ['{"action": "click", "args": {"name": "В корзину"}}', DONE]
    r, _d, _a, _n = make_runner("открой магазин", answers, drv=drv)
    out = r.run()
    clicks = [d for d in drv.done if d[0] == A.CLICK]
    assert len(clicks) == 2, "первый клик провалился — повторили"  # попытка и повтор
    assert out == "Готово.", out


# ---------- 3. шаги агента озвучиваются (notify получает каждый шаг) ----------
def test_every_step_is_announced():
    answers = ['{"action": "click", "args": {"name": "В корзину"}}', DONE]
    r, _d, _a, notifies = make_runner("открой магазин", answers)
    r.run()
    assert any("нажму" in t or "В корзину" in t for t in notifies), notifies


if __name__ == "__main__":
    for n, fn in sorted(list(globals().items())):
        if n.startswith("test_") and callable(fn):
            fn()
            print("OK", n)
    print("ALL OK agent extras")
