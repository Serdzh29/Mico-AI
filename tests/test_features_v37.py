import os as _os, sys as _sys, time, json, tempfile, threading
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import notes as N
import pomodoro as P
import diagnose as D
import updates as U
import version as V


def test_notes_commands():
    assert N.parse("запиши: купить молоко") == ("add", "купить молоко")
    assert N.parse("Запиши молоко") == ("add", "молоко")
    assert N.parse("что я записывал сегодня") == ("list", "today")
    assert N.parse("мои заметки") == ("list", "all")
    assert N.parse("запиши") is None and N.parse("открой блокнот") is None


def test_notes_list_scopes():
    now = time.time()
    items = [{"ts": now - 2 * 86400, "text": "старое"}, {"ts": now - 60, "text": "новое"}]
    today = N.format_list(items, "today", now)
    assert "новое" in today and "старое" not in today
    assert "старое" in N.format_list(items, "all", now)
    assert N.format_list([], "today", now).startswith("Заметок за сегодня нет")


def test_pomodoro_full_cycle_and_stop():
    done, msgs = [], []
    p = P.Pomodoro(msgs.append, lambda: done.append(1), work=0.15, rest=0.15)
    assert p.start() and p.running()
    assert not p.start()                                   # второй запуск не нужен
    time.sleep(0.4)
    assert done == [1], done                               # один завершённый рабочий цикл
    assert any("работы" in m for m in msgs) and any("Перерыв" in m for m in msgs)
    p.stop()
    assert not p.running()
    p2 = P.Pomodoro(msgs.append, lambda: None, work=5, rest=5)
    p2.start()
    assert p2.stop() is True and not p2.running()


def test_model_errors_have_advice():
    import requests
    assert "Ollama не запущена" in D.explain_model_error(requests.exceptions.ConnectionError(), "m")
    assert "долго" in D.explain_model_error(requests.exceptions.Timeout(), "m")
    r = requests.Response(); r.status_code = 404
    e = requests.HTTPError(response=r)
    assert "ollama pull qwen" in D.explain_model_error(e, "qwen")


def test_environment_report_marks_failures():
    rep = D.environment_report([("Один", lambda: (True, "")), ("Два", lambda: (False, "сделай X")),
                                ("Три", lambda: 1 / 0)])
    assert "✓ Один" in rep and "✗ Два — сделай X" in rep and "✗ Три" in rep


def test_update_channels_and_sha256():
    data = {"version": "34", "url": "u", "sha256": "ABC",
            "channels": {"beta": {"version": "35", "url": "ub", "sha256": "DEF"}}}
    p = _os.path.join(tempfile.mkdtemp(), "f.bin")
    open(p, "wb").write(b"hello")
    import hashlib
    good = hashlib.sha256(b"hello").hexdigest()
    assert U.verify_sha256(p, good.upper()) and not U.verify_sha256(p, "00")
    assert U.parse('{"version": "1", "sha256": "xx"}')["sha256"] == "xx"


def test_recent_changes_lists_latest_first():
    text = V.recent_changes(2)
    lines = [l for l in text.splitlines() if l.startswith("Версия")]
    assert len(lines) == 2 and lines[0] == f"Версия {V.APP_VERSION}:"


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
