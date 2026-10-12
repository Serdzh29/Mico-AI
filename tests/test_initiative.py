import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import initiative as I


def test_looks_only_when_window_changes():
    g = I.Gate(min_gap=900)
    assert g.should_look(now=0, window=1, busy=False, blocked=False, paused=False)
    g.looked(0, 1)
    assert not g.should_look(now=1000, window=1, busy=False, blocked=False, paused=False)   # то же окно
    assert not g.should_look(now=500, window=2, busy=False, blocked=False, paused=False)   # интервал не прошёл
    assert g.should_look(now=901, window=2, busy=False, blocked=False, paused=False)


def test_never_looks_when_busy_blocked_paused_or_no_window():
    g = I.Gate()
    for kwargs in [dict(busy=True, blocked=False, paused=False), dict(busy=False, blocked=True, paused=False),
                   dict(busy=False, blocked=False, paused=True)]:
        assert not g.should_look(now=0, window=1, **kwargs)
    assert not g.should_look(now=0, window=None, busy=False, blocked=False, paused=False)


def test_repeat_detection():
    g = I.Gate()
    g.remember("Ты открыл новости про погоду в Москве")
    assert g.is_repeat("Снова погода в Москве, опять новости")
    assert not g.is_repeat("Видео с котиком выглядит уютно")
    assert g.is_repeat("")                                  # пустую фразу не говорим


def test_memory_keeps_last_phrases_only():
    g = I.Gate()
    for i in range(10):
        g.remember(f"фраза номер {i}")
    assert len(g.recent) == I.KEEP


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
