"""Память разговора: журнал на диске, вспоминание по датам и темам, очистка, сарказм.
Перевод и поиск файлов удалены — проверяем, что их нигде не осталось."""
import os, re, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# журнал пишем во временную папку, а не в настоящий профиль пользователя
os.environ["APPDATA"] = tempfile.mkdtemp()

import recall as R
import smart
from dialog import Dialog

DAY = 86400


def test_parse_understands_dates_and_topics():
    now = time.time()
    assert R.parse("о чём мы говорили вчера?", now)["label"] == "вчера"
    assert R.parse("что я спрашивал позавчера", now)["label"] == "позавчера"
    assert R.parse("о чём мы говорили за последние 3 дня", now)["label"] == "за последние 3 дн."
    spec = R.parse("о чём говорили про принтер", now)
    assert spec and spec["topic"] == ["принтер"]
    assert R.parse("помнишь, что я писал на прошлой неделе", now)["label"] == "за прошлую неделю"


def test_parse_ignores_ordinary_questions():
    for q in ["включи музыку", "что писать в письме начальнику", "помнишь как включить блютуз",
              "о чём говорить с другом?", "что я делал час назад"]:
        assert R.parse(q) is None, q


def test_answer_lists_pairs_and_filters_by_topic():
    now = time.time()
    rows = [(now - 3600, "user", "как настроить принтер"), (now - 3599, "mico", "Открой «Принтеры»"),
            (now - 1800, "user", "какая погода"), (now - 1799, "mico", "Облачно, +12")]
    spec = {"label": "за последнюю неделю", "topic": None}
    text = R.answer(rows, spec)
    assert "как настроить принтер" in text and "какая погода" in text
    text = R.answer(rows, {"label": "за последнюю неделю", "topic": ["принтер"]})
    assert "принтер" in text and "погода" not in text


def test_answer_says_so_when_nothing_found():
    text = R.answer([], {"label": "вчера", "topic": None})
    assert "ничего не нашёл" in text


def test_pairs_skip_mico_replies_without_question():
    rows = [(1, "mico", "привет"), (2, "user", "вопрос"), (3, "mico", "ответ")]
    assert R.pairs(rows) == [(2, "вопрос", "ответ")]


def test_dialog_persists_turns_and_survives_broken_store():
    seen = []
    d = Dialog(persist=lambda ts, role, text: seen.append((role, text)))
    d.add("user", "привет")
    d.add("mico", "Привет!")
    assert seen == [("user", "привет"), ("mico", "Привет!")]
    broken = Dialog(persist=lambda *a: 1 / 0)
    broken.add("user", "не должно упасть")                  # журнал сломался — разговор идёт дальше
    assert broken.recent()


def test_store_round_trip_and_purge_and_wipe():
    import storage
    st = storage.Store()
    now = time.time()
    st.add_chat(now - 2 * DAY, "user", "старая реплика")
    st.add_chat(now - 60, "user", "вчерашний вопрос про принтер")
    st.add_chat(now - 30, "mico", "ответ про принтер")
    rows = st.chats_between(now - DAY, now + 1)
    assert [r[2] for r in rows] == ["вчерашний вопрос про принтер", "ответ про принтер"]
    st.purge(1)                                              # старше суток — уходит
    assert all(r[2] != "старая реплика" for r in st.chats_between(now - 10 * DAY, now + 1))
    st.wipe()
    assert st.chats_between(now - 10 * DAY, now + 1) == []


def _stub_windows_only():
    """На Linux нет библиотек Windows: подменяем их заглушками, только чтобы импортировать brain."""
    import importlib
    from unittest import mock
    for name in ["mss", "win32gui", "win32process", "win32api", "win32con", "PIL", "PIL.Image", "psutil"]:
        try:
            importlib.import_module(name)
        except Exception:
            sys.modules[name] = mock.MagicMock()


def test_persist_respects_memory_switch():
    _stub_windows_only()
    import brain as B
    calls = []

    class Stub:
        cfg = {"memory_on": False}

        class store:
            @staticmethod
            def add_chat(*a):
                calls.append(a)
    B.Brain._persist_turn(Stub(), time.time(), "user", "не должно сохраниться")
    assert calls == []
    Stub.cfg = {"memory_on": True}
    B.Brain._persist_turn(Stub(), time.time(), "user", "сохраняем")
    assert len(calls) == 1


def test_sarcasm_is_answered_but_plain_yes_is_not():
    assert smart.smalltalk("ага, конечно") is not None
    assert smart.smalltalk("очень смешно") is not None
    assert smart.smalltalk("ага") is None                    # одно «ага» бывает искренним


def _source_files():
    for name in os.listdir(ROOT):
        if name.endswith(".py") and not name.startswith("test_"):
            yield name, open(os.path.join(ROOT, name), encoding="utf-8").read()


def test_translation_and_file_search_are_gone():
    banned = [r"def translate\b", r"translate_selection", r"hotkey_translate", r"\bhk_tr\b",
              r"find_files", r"\"find_file\"", r"_index_reply", r"_index_command", r"import.*\bindexer\b",
              r"Chip\(\"find\"", r"Chip\(\"clip\"", r"переведи буфер", r"Перевести буфер"]
    found = []
    for name, src in _source_files():
        for pat in banned:
            if re.search(pat, src):
                found.append((name, pat))
    assert not found, found
    assert not os.path.exists(os.path.join(ROOT, "indexer.py"))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("OK test_memory_recall")
