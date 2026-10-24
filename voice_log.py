"""Журнал ошибок голоса: полный трейсбек пишется в %APPDATA%\\Mico\\voice_error.log.
В чат попадает короткая строка, а причина (например, NameError внутри библиотеки) остаётся в файле."""
import datetime
import os
import traceback

from storage import APPDIR

LOG_PATH = os.path.join(APPDIR, "voice_error.log")


def record(where, exc):
    """Пишет полный трейсбек и возвращает короткое сообщение для пользователя."""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} · {where}\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except OSError:
        pass
    return f"{where}: {type(exc).__name__}: {exc} (подробности: voice_error.log)"
