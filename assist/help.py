"""Помощь с ошибками: последние строки журнала и решение, которое Mico AI находит сам по тексту ошибки.
Ничего никуда не отправляется: модель работает на этом компьютере. Приложения Windows не открываются."""
import os, re

LOG_PHRASE = re.compile(r"^(?:покажи|открой|дай|выведи)?\s*(?:последние\s+)?(?:строки\s+)?(?:журнал\w*|лог\w*)"
                        r"(?:\s+(?:ошибок|ошибки|ошибка|программы|mico))?$|^покажи\s+ошибки$")
HELP_PHRASE = re.compile(r"найди\s+(?:решение|ответ)|реши\w*\s+(?:проблему|ошибку)|открой\s+справку"
                         r"|справка\s+windows|помощь\s+windows")
LOG_FILES = ("crash.log", "launch.log", "startup.log")
TAIL_LINES = 25
MAX_CHARS = 1500


def command(ql):
    low = (ql or "").strip(" .!?").replace("ё", "е")
    if LOG_PHRASE.match(low):
        return "log"
    if HELP_PHRASE.search(low):
        return "help"
    return None


def log_dir():
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Mico")


def log_tail(folder=None):
    """Последние строки первого найденного журнала ошибок. Возвращает (имя файла, текст) или (None, '')."""
    folder = folder or log_dir()
    for name in LOG_FILES:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()[-TAIL_LINES:]
            except OSError:
                continue
            text = "".join(lines).strip()
            if text:
                return name, text[-MAX_CHARS:]
    return None, ""


_LAST = {"title": "", "text": ""}     # последняя ошибка, которую видел Mico


def remember(title, text):
    """Запоминает ошибку, чтобы «найди решение» работало без открытия других приложений."""
    if text:
        _LAST["title"], _LAST["text"] = str(title or "")[:200], str(text)[:MAX_CHARS]


def last_error():
    """(заголовок, текст) последней ошибки или None."""
    return (_LAST["title"], _LAST["text"]) if _LAST["text"] else None


def solution_prompt(title, text):
    """Просьба модели: объяснить ошибку и предложить шаги. Без выдуманных фактов."""
    return ("Пользователь видит ошибку «" + str(title) + "». Текст: " + str(text)[:MAX_CHARS] + "\n"
            "Объясни коротко, что означает эта ошибка, и предложи 2–4 понятных шага, что сделать. "
            "Пиши простыми словами. Если по тексту не понятно, в чём причина, так и скажи и предложи, что уточнить. "
            "Ничего не выдумывай.")
