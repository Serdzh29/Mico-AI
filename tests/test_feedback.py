import os as _os, sys as _sys, json, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import feedback as F


def test_entry_kinds_and_limits():
    e = F.make_entry("problem", "  текст  ", "q" * 500, "a" * 500)
    assert e["kind"] == "problem" and e["text"] == "текст"
    assert len(e["question"]) == F.MAX_CONTEXT and len(e["answer"]) == F.MAX_CONTEXT
    assert len(F.make_entry("idea", "x" * 5000)["text"]) == F.MAX_TEXT
    try:
        F.make_entry("spam")
        assert False
    except ValueError:
        pass


def test_survey_once_after_a_week():
    now = 10 * 86400
    assert not F.should_show_survey({}, now)                                   # нет даты первого запуска
    assert not F.should_show_survey({"first_run": now - 3 * 86400}, now)        # рано
    assert F.should_show_survey({"first_run": now - 8 * 86400}, now)            # пора
    assert not F.should_show_survey({"first_run": now - 8 * 86400, "survey_done": True}, now)


def test_export_has_no_times_and_keeps_text():
    entries = [F.make_entry("up", "", "вопрос", "ответ"), F.make_entry("idea", "хочу X")]
    data = json.loads(F.export_json(entries))
    assert all("time" not in d for d in data)
    assert data[1]["text"] == "хочу X"


def test_summary_counts():
    s = F.summary([F.make_entry("up"), F.make_entry("up"), F.make_entry("problem", "x")])
    assert s["up"] == 2 and s["problem"] == 1 and s["down"] == 0


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
