import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import breaks as B


def test_reminds_once_after_an_hour_of_work():
    w = B.BreakWatch(break_minutes=60, start=0)
    assert w.tick(now=3599, idle=0) is None
    assert "60 мин" in w.tick(now=3600, idle=0)
    assert w.tick(now=3700, idle=0) is None                 # один раз за сессию


def test_idle_break_starts_new_session():
    w = B.BreakWatch(break_minutes=60, start=0)
    w.tick(now=3600, idle=0)                                # напомнили
    w.tick(now=4000, idle=B.IDLE_RESET + 1)                 # отошёл на перерыв
    assert w.tick(now=4000 + 3600, idle=0) is not None      # снова через час работы


def test_cooldown_between_reminders():
    w = B.BreakWatch(break_minutes=5, start=0)
    assert w.tick(now=300, idle=0) is not None
    w.tick(now=600, idle=B.IDLE_RESET + 1)                  # перерыв, сессия заново
    assert w.tick(now=600 + 300, idle=0) is None             # ещё нет 15 минут с прошлого напоминания
    assert w.tick(now=300 + B.COOLDOWN, idle=0) is not None   # после паузы в 15 минут — снова можно


def test_not_allowed_keeps_counting_but_stays_silent():
    w = B.BreakWatch(break_minutes=5, start=0)
    assert w.tick(now=400, idle=0, allowed=False) is None   # тишина: молчим
    assert w.tick(now=401, idle=0, allowed=True) is not None  # но отсчёт шёл, напоминание есть


def test_minutes_setting_applies_live():
    w = B.BreakWatch(break_minutes=60, start=0)
    w.set_minutes(10)
    assert w.tick(now=600, idle=0) is not None


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
