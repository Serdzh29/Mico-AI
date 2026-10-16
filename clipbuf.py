"""История копирования (бета): последние скопированные тексты, поиск по ним.
Не сохраняем пароли, номера карт, ключи и всё, что скопировано из менеджеров паролей.
Здесь только логика, хранение — в storage.Store, чтение буфера — в main.py."""
import re, time

KEEP = 200                  # сколько последних копий помним
MAX_LEN = 2000
EXCLUDED = {"keepass.exe", "keepassxc.exe", "1password.exe", "bitwarden.exe", "lastpass.exe",
            "dashlane.exe", "keeper.exe", "mico.exe", "python.exe", "pythonw.exe"}
SECRET_WORDS = re.compile(r"пароль|password|passwd|пин[- ]?код|\bpin\b|токен|\btoken\b|api[ _-]?key|секрет|"
                          r"\bsecret\b|\bcvv\b|\bcvc\b|ключ доступа", re.I)
CARD_LIKE = re.compile(r"[\d -]{13,23}")
SEARCH = re.compile(r"^(?:найди|поищи|покажи|что)\s+(?:мне\s+)?(?:что\s+)?(?:я\s+)?"
                    r"(?:копировал\w*|скопировал\w*|в\s+истории\s+копирования)\s*(?:про|о|об|по|с)?\s*(.*)$")
FORGET = re.compile(r"^(?:забудь|удали|очисти)\s+(?:мою\s+)?историю\s+копирования$")


def command(ql):
    """('search', запрос) | ('forget', None) | None."""
    s = (ql or "").strip(" .!?")
    if FORGET.match(s):
        return ("forget", None)
    m = SEARCH.match(s)
    if m:
        return ("search", m.group(1).strip())
    return None


def looks_secret(text):
    t = text.strip()
    if SECRET_WORDS.search(t):
        return True
    if CARD_LIKE.fullmatch(t) and len(re.sub(r"\D", "", t)) >= 13:
        return True                                   # номер карты, возможно с пробелами
    if (8 <= len(t) <= 64 and " " not in t and not t.lower().startswith(("http", "www."))
            and re.search(r"\d", t) and re.search(r"[A-Za-zА-Яа-я]", t) and re.search(r"[^A-Za-zА-Яа-я0-9]", t)):
        return True                                   # одно слово из букв, цифр и знаков: похоже на пароль
    return False


def should_keep(text, proc):
    t = (text or "").strip()
    if not t or len(t) > MAX_LEN:
        return False
    if (proc or "").lower() in EXCLUDED:
        return False
    return not looks_secret(t)


class Recorder:
    """Смотрит на буфер и запоминает новые тексты. Повтор того же текста не записывает дважды."""

    def __init__(self, store):
        self.store, self.last = store, None

    def offer(self, text, proc, now=None):
        if text == self.last or text is None:
            return False
        self.last = text
        if not should_keep(text, proc):
            return False
        self.store.add_clip(now or time.time(), text.strip())
        return True


def snippet(text, width=110):
    s = " ".join(text.split())
    return s if len(s) <= width else s[: width - 1] + "…"


def format_hits(hits, now_fmt):
    """hits: [(ts, text)] — строки для ответа."""
    return "\n".join(f"{now_fmt(ts)} — {snippet(text)}" for ts, text in hits)


# ----- помощник по буферу обмена (WI): текст ошибки — предложить объяснить -----
ERROR_HINT = re.compile(r"traceback|exception|error:|errno|hresult|0x[0-9a-f]{6,8}|failed|access is denied|"
                        r"ошибк|исключени|не удалось|отказано в доступе|нет доступа|сбой|не найден|"
                        r"not found|fatal|warning:", re.I)


def looks_like_error(text):
    """Похоже ли скопированное на текст ошибки. Секреты — никогда (даже если похоже на ошибку)."""
    t = (text or "").strip()
    if not (12 <= len(t) <= 3000):
        return False
    if looks_secret(t):
        return False
    return bool(ERROR_HINT.search(t))
