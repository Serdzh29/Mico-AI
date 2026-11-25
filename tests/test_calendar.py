"""Календарь (calendar_book.py): разбор «запиши в календарь …», списков и удаления, напоминания.
Время фиксируем: «сейчас» — четверг 29.10.2026, 22:22. Запуск: python tests/test_calendar.py"""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from win import calendar as C

NOW = time.mktime((2026, 10, 29, 22, 22, 0, 0, 0, -1))


def at(y, mo, d, h=0, mi=0):
    return int(time.mktime((y, mo, d, h, mi, 0, 0, 0, -1)))


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_add_tomorrow_with_time():
    kind, ev = C.parse("запиши в календарь завтра в 18:30 созвон", NOW)
    check(kind == "add" and ev["due"] == at(2026, 10, 30, 18, 30), ev)
    check(ev["text"] == "созвон", ev)


def test_add_with_russian_month_name():
    kind, ev = C.parse("запиши в календарь 15 ноября в 10:00 стоматолог", NOW)
    check(kind == "add" and ev["due"] == at(2026, 11, 15, 10, 0) and ev["text"] == "стоматолог", ev)


def test_dot_date_and_time_with_dot_are_not_confused():
    kind, ev = C.parse("запиши в календарь 5.11 в 18.30 встреча с Леной", NOW)
    check(ev["due"] == at(2026, 11, 5, 18, 30), ev)
    check(ev["text"] == "встреча с Леной", ev)


def test_date_only_defaults_to_nine_am():
    kind, ev = C.parse("запиши в календарь послезавтра сдать отчёт", NOW)
    check(ev["due"] == at(2026, 10, 31, 9, 0) and ev["text"] == "сдать отчёт", ev)


def test_time_only_is_today_or_tomorrow():
    kind, ev = C.parse("запиши в календарь в 23:00 лечь спать", NOW)
    check(ev["due"] == at(2026, 10, 29, 23, 0), "23:00 ещё впереди сегодня")
    kind, ev = C.parse("запиши в календарь в 8 утра позвонить маме", NOW)
    check(ev["due"] == at(2026, 10, 30, 8, 0), "8 утра уже прошло — это завтра")


def test_hours_with_evening_word():
    kind, ev = C.parse("запиши в календарь завтра в 6 вечера ужин", NOW)
    check(ev["due"] == at(2026, 10, 30, 18, 0), ev)


def test_past_date_without_year_means_next_year():
    kind, ev = C.parse("запиши в календарь 3 октября в 10:00 ретро", NOW)
    check(ev["due"] == at(2027, 10, 3, 10, 0), ev)


def test_no_date_or_time_asks_for_time():
    check(C.parse("запиши в календарь созвон", NOW) == ("need_time", None))


def test_list_ranges():
    kind, (t0, t1, label) = C.parse("что у меня в календаре на сегодня", NOW)
    check(kind == "list" and t0 == at(2026, 10, 29) and t1 == at(2026, 10, 30) and label == "на сегодня", label)
    kind, (t0, t1, label) = C.parse("календарь на неделю", NOW)
    check(t1 - t0 == 7 * 86400 and label == "на неделю", label)
    kind, (t0, t1, label) = C.parse("что в календаре завтра", NOW)
    check(t0 == at(2026, 10, 30) and label == "на завтра", label)


def test_delete_by_number():
    check(C.parse("удали событие 3", NOW) == ("delete", 3))
    check(C.parse("убери запись из календаря 12", NOW) == ("delete", 12))


def test_other_phrases_are_not_calendar():
    for q in ("запиши: купить молоко", "открой блокнот", "что такое календарь григориански", "запомни, что я устал"):
        check(C.parse(q, NOW) is None, f"не календарь: {q}")


def test_reminder_ten_minutes_before_only_if_still_ahead():
    due = NOW + 3600
    check(C.reminder_time(due, NOW) == due - C.REMIND_BEFORE)
    check(C.reminder_time(NOW + 300, NOW) is None, "за пять минут до события уже поздно")


def test_format_list_shows_ids_and_empty_case():
    check("пусто" in C.format_list([], "на сегодня"))
    text = C.format_list([(7, at(2026, 10, 30, 18, 30), "созвон")], "на завтра")
    check("№7" in text and "созвон" in text and "30.10 в 18:30" in text, text)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK calendar")
