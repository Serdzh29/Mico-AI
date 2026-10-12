"""Напоминания, которые переживают перезапуск Mico. Хранятся в %APPDATA%\\Mico\\reminders.json."""
import threading, time, uuid

_store = None                  # зашифрованное хранилище (Store); задаётся через bind() при запуске
_lock = threading.Lock()
_timers = {}


def bind(store):
    global _store
    _store = store


def _load():
    return _store.list_reminders() if _store else []


def _remove(rid):
    with _lock:
        if _store:
            _store.delete_reminder(rid)
        _timers.pop(rid, None)


def _schedule(item, notify):
    delay = max(0.0, item["due"] - time.time())

    def fire():
        notify("напоминание: " + item["text"])
        if item.get("rule"):                              # повторяющееся — переносим на следующий срок
            _reschedule_recurring(item, notify)
        else:
            _remove(item["id"])
    t = threading.Timer(delay, fire)
    t.daemon = True
    t.start()
    _timers[item["id"]] = t


def _reschedule_recurring(item, notify):
    import recur
    days, hour, minute = recur.decode(item["rule"])
    item["due"] = int(recur.next_due(days, hour, minute, time.time()))
    with _lock:
        if _store:
            _store.add_reminder(item["id"], item["due"], item["text"], item["rule"])
    _schedule(item, notify)


def add(text, due, notify, rule=None):
    item = {"id": uuid.uuid4().hex, "text": text, "due": int(due), "rule": rule}
    with _lock:
        if _store:
            _store.add_reminder(item["id"], item["due"], item["text"], rule)
    _schedule(item, notify)
    return item


def restore(notify):
    """При запуске Mico заново ставит таймеры. Повторяющиеся переносятся на следующий срок, прошедшие — удаляются."""
    import recur
    for it in list(_load()):
        if it.get("rule"):
            days, hour, minute = recur.decode(it["rule"])
            if it["due"] <= time.time():
                it["due"] = int(recur.next_due(days, hour, minute, time.time()))
                with _lock:
                    if _store:
                        _store.add_reminder(it["id"], it["due"], it["text"], it["rule"])
            _schedule(it, notify)
        elif it["due"] > time.time():
            _schedule(it, notify)
        else:
            _remove(it["id"])


def today(now=None):
    """Напоминания на сегодня, по времени."""
    now = now or time.time()
    lt = time.localtime(now)
    start = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
    end = start + 86400
    return sorted((i for i in _load() if start <= i["due"] < end and i["due"] >= now), key=lambda i: i["due"])
