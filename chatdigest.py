"""Пересказ разговора по дням: раз в сутки модель коротко пересказывает прошедший день,
и «о чём мы говорили вчера» отвечает пересказом, а не длинным списком реплик.
Модель вызывается только для прошедших дней без пересказа и только в фоне.
Чистая логика — в tests/test_chatdigest.py."""
import time

import recall

DAY = 86400
MIN_ROWS = 4          # меньше двух обменов репликами — пересказывать нечего
BACK_DAYS = 30        # сколько прошлых дней проверяем при фоновом проходе
MAX_CHARS = 5000      # сколько текста дня отдаём модели (берём конец дня)
SUMMARY_MAX = 500     # длина пересказа, который сохраняем


def key_of(ts):
    """Ключ дня по местному времени: «2026-10-12». Сортируется как строка."""
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def bounds(key):
    """Начало и конец дня (по местному времени) для ключа."""
    y, m, d = (int(x) for x in key.split("-"))
    return time.mktime((y, m, d, 0, 0, 0, 0, 0, -1)), time.mktime((y, m, d + 1, 0, 0, 0, 0, 0, -1))


def missing(now, enough_rows, has_summary):
    """Прошлые дни (не сегодня), где есть разговор, но ещё нет пересказа. Старые дни — первыми."""
    today = key_of(now)
    keys = {key_of(now - i * DAY) for i in range(1, BACK_DAYS + 1)}
    out = []
    for key in sorted(keys):
        if key == today or has_summary(key):
            continue
        t0, t1 = bounds(key)
        if enough_rows(t0, t1):
            out.append(key)
    return out


def prompt(rows):
    """Реплики дня → запрос к модели. None — реплик мало или пар «вопрос — ответ» нет."""
    if len(rows) < MIN_ROWS or not recall.pairs(rows):
        return None
    lines = []
    for _ts, q, a in recall.pairs(rows):
        lines.append(f"Пользователь: {q}")
        if a:
            lines.append(f"Mico AI: {a}")
    text = "\n".join(lines)[-MAX_CHARS:]
    return ("Ниже реплики одного дня разговора с пользователем. Напиши пересказ на русском в 2–3 коротких "
            "предложениях: о чём говорили и что было важно пользователю. Только то, что есть в репликах, "
            "без догадок, без списков и без приветствия.\n\n" + text)


def clean(text):
    """Ответ модели → одна короткая строка без лишних кавычек и переносов."""
    s = " ".join(str(text).split()).strip(" \"'«»")
    return s[:SUMMARY_MAX]
