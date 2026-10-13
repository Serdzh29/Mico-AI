"""Пересказ разговора по дням: какие дни пересказывать, что отдать модели, как показать «о чём говорили вчера»."""
import os, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["APPDATA"] = tempfile.mkdtemp()          # журнал пишем во временную папку

import chatdigest as D
import recall as R

DAY = 86400


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_day_key_and_bounds_round_trip():
    now = time.mktime((2026, 10, 12, 15, 30, 0, 0, 0, -1))
    key = D.key_of(now)
    check(key == "2026-10-12", key)
    t0, t1 = D.bounds(key)
    check(t0 <= now < t1 and D.key_of(t0) == key and D.key_of(t1) == "2026-10-13")


def test_missing_skips_today_done_days_and_quiet_days():
    now = time.time()
    yesterday, day_before, three_ago = (D.key_of(now - i * DAY) for i in (1, 2, 3))
    # есть разговор в трёх днях, пересказ уже готов для позавчера, а в три дня назад — мало реплик
    rich = {yesterday, day_before, three_ago}

    def enough_rows(t0, t1):
        return D.key_of(t0) in rich and D.key_of(t0) != three_ago

    def has_summary(key):
        return key == day_before

    got = D.missing(now, enough_rows, has_summary)
    check(got == [yesterday], got)
    check(D.key_of(now) not in got, "сегодняшний день не пересказываем — он ещё идёт")


def test_prompt_needs_enough_exchanges_and_keeps_order():
    check(D.prompt([(1, "user", "привет")]) is None, "мало реплик")
    rows = [(1, "user", "как настроить принтер"), (2, "mico", "Открой «Принтеры»"),
            (3, "user", "а погода?"), (4, "mico", "Облачно")]
    text = D.prompt(rows)
    check(text and text.index("принтер") < text.index("погода"), text)
    check("без догадок" in text)


def test_clean_makes_one_short_line():
    check(D.clean("  «Говорили про\nпринтер.»  ") == "Говорили про принтер.", D.clean("  «Говорили про\nпринтер.»  "))
    check(len(D.clean("а" * 2000)) <= D.SUMMARY_MAX)


def test_answer_uses_summary_for_past_day_and_raw_for_the_rest():
    now = time.time()
    yesterday = D.key_of(now - DAY)
    t_y = time.mktime(time.strptime(yesterday + " 10:00", "%Y-%m-%d %H:%M"))
    t_today = now - 60
    rows = [(t_y, "user", "как настроить принтер"), (t_y + 5, "mico", "Открой «Принтеры»"),
            (t_today, "user", "какая погода")]
    spec = {"label": "за последнюю неделю", "topic": None}
    text = R.answer_days(rows, spec, {yesterday: "Настраивали принтер и спрашивали про Wi-Fi."})
    check("Настраивали принтер" in text, text)           # вчера — пересказом
    check("какая погода" in text, text)                  # сегодня пересказа нет — реплика как была
    check("как настроить принтер" not in text, text)     # сырых реплик вчера уже нет
    text = R.answer_days(rows, {"label": "вчера", "topic": ["принтер"]}, {yesterday: "x"})
    check("как настроить принтер" in text and "погода" not in text, text)   # поиск по теме — по репликам


def test_store_keeps_summaries_and_purge_wipe_remove_them():
    import storage
    st = storage.Store()
    now = time.time()
    k_old, k_new = D.key_of(now - 5 * DAY), D.key_of(now - DAY)
    st.add_day_summary(k_old, "старый день", now - 5 * DAY)
    st.add_day_summary(k_new, "вчерашний день", now - DAY)
    got = st.day_summaries(D.key_of(now - 7 * DAY), D.key_of(now))
    check(got == {k_old: "старый день", k_new: "вчерашний день"}, got)
    check(st.has_day_summary(k_new) and not st.has_day_summary("1999-01-01"))
    st.purge(2)
    got = st.day_summaries(D.key_of(now - 7 * DAY), D.key_of(now))
    check(k_old not in got and k_new in got, got)
    st.wipe()
    check(st.day_summaries("0000-00-00", "9999-99-99") == {})


def test_digest_past_days_writes_one_summary_per_day_and_survives_model_errors():
    import importlib
    from unittest import mock
    for name in ["mss", "win32gui", "win32process", "win32api", "win32con", "PIL", "PIL.Image", "psutil"]:
        try:
            importlib.import_module(name)
        except Exception:
            sys.modules[name] = mock.MagicMock()
    import brain as B

    now = time.time()
    yesterday = D.key_of(now - DAY)
    t_y = time.mktime(time.strptime(yesterday + " 12:00", "%Y-%m-%d %H:%M"))
    saved = {}
    rows = [(t_y, "user", "как настроить принтер"), (t_y + 1, "mico", "Открой «Принтеры»"),
            (t_y + 2, "user", "а Wi-Fi?"), (t_y + 3, "mico", "Включи в трее")]

    class FakeStore:
        def count_chat(self, t0, t1):
            return len(rows) if D.key_of(t0) == yesterday else 0

        def has_day_summary(self, key):
            return key in saved

        def chats_between(self, t0, t1):
            return rows if D.key_of(t0) == yesterday else []

        def add_day_summary(self, key, text, ts):
            saved[key] = text

    class Stub:
        cfg = {"memory_on": True, "text_model": "m"}
        store = FakeStore()
        calls = 0

        def _chat(self, prompt, model, **kw):
            Stub.calls += 1
            check("принтер" in prompt and model == "m")
            return "Настраивали принтер и подключали Wi-Fi."

    check(B.Brain.digest_past_days(Stub()) == 1)
    check(saved[yesterday] == "Настраивали принтер и подключали Wi-Fi.", saved)
    check(B.Brain.digest_past_days(Stub()) == 0 and Stub.calls == 1, "второй раз модель не вызываем")

    class Broken(Stub):
        cfg = {"memory_on": True, "text_model": "m"}
        store = FakeStore()
        saved_keys = []

        def _chat(self, *a, **kw):
            raise RuntimeError("модель не запущена")

    saved.clear()
    try:
        B.Brain.digest_past_days(Broken())
    except RuntimeError:
        pass                                             # в фоновом цикле это ловится и повторяется в следующий час
    check(saved == {}, "при ошибке модели пересказ не записываем")

    class Off(Stub):
        cfg = {"memory_on": False, "text_model": "m"}

    check(B.Brain.digest_past_days(Off()) == 0, "при выключенной памяти ничего не делаем")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("OK test_chatdigest")
