import datetime
import os as _os, sys as _sys, time, datetime
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import recur as R
import features as F


def test_recurring_parse_variants():
    p = R.parse("напомни каждый понедельник в 9:00 проверить отчёт")
    assert p["days"] == (0,) and p["hour"] == 9 and p["minute"] == 0
    assert p["text"] == "проверить отчёт"                      # «ё» сохраняется из оригинала
    assert R.parse("Напомни каждый день в 8 выпить воду")["days"] == R.ALL
    assert R.parse("напомни по будням в 10:30 созвон")["days"] == R.WORKDAYS
    assert R.parse("напомни через час позвонить") is None
    assert R.parse("напомни каждый понедельник в 25:00 текст") is None


def test_recurring_rule_roundtrip_and_next_occurrence():
    rule = R.encode((0, 3), 9, 30)
    assert R.decode(rule) == ((0, 3), 9, 30)
    mon_10 = datetime.datetime(2026, 10, 12, 10, 0).timestamp()          # понедельник, 10:00
    nxt = datetime.datetime.fromtimestamp(R.next_due((0,), 9, 0, mon_10))
    assert nxt.date() == datetime.date(2026, 10, 19) and nxt.hour == 9  # следующий понедельник
    mon_8 = datetime.datetime(2026, 10, 12, 8, 0).timestamp()
    assert datetime.datetime.fromtimestamp(R.next_due((0,), 9, 0, mon_8)).date() == datetime.date(2026, 10, 12)


