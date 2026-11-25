"""Мессенджеры: «открой телеграм и напиши алексею привет» → программа, контакт, текст.

Главное здесь — имя контакта. Пользователь говорит его в дательном или творительном падеже
(«алексею», «мамуле», «саше»), а в списке чатов оно стоит в именительном («Алексей», «Мама»).
Поэтому модуль строит варианты именительного падежа и ищет среди подписей чатов то, что подходит.

Чистая логика, без Windows: разбор фразы, варианты имени, поиск в списке. Нажатия делает agent.py."""
import difflib, os, re

# Программы, которые агент считает мессенджерами (в нижнем регистре, без «ё»)
MESSENGERS = {"телеграм", "телеграмм", "telegram", "тг", "max", "макс", "ватсап", "вотсап", "whatsapp",
              "вайбер", "viber", "discord", "дискорд", "teams", "майкрософт teams", "microsoft teams", "тимс"}

# Клавиша поиска в каждом мессенджере: где-то Ctrl+F, где-то быстрый переключатель Ctrl+K / Ctrl+E
SEARCH_HOTKEY = {"discord": "ctrl+k", "teams": "ctrl+e", "майкрософт teams": "ctrl+e",
                 "microsoft teams": "ctrl+e", "тимс": "ctrl+e"}


# Чем открыть верхний результат поиска, если окно не отдаёт список чатов (Telegram, MAX и другие рисуют его сами).
# В WhatsApp и Teams сначала нужна стрелка вниз, в остальных хватает Enter.
PICK_KEYS = {"whatsapp": ("down", "enter"), "ватсап": ("down", "enter"), "вотсап": ("down", "enter"),
             "teams": ("down", "enter"), "тимс": ("down", "enter"), "майкрософт teams": ("down", "enter"),
             "microsoft teams": ("down", "enter")}


def pick_keys(app):
    return PICK_KEYS.get(_norm(app), ("enter",))


def search_hotkey(app):
    """Чем открывать поиск в этом мессенджере: Ctrl+F в большинстве, но не везде."""
    return SEARCH_HOTKEY.get(_norm(app), "ctrl+f")


LAUNCH_PATHS = {
    # Известные установки «для себя»: их нет в PATH, ищем по стандартным адресам.
    # Только эти адреса — ничего не выдумываем и лишнего не трогаем.
    "телеграм": (r"%APPDATA%\Telegram Desktop\Telegram.exe",),
    "telegram": (r"%APPDATA%\Telegram Desktop\Telegram.exe",),
    "тг": (r"%APPDATA%\Telegram Desktop\Telegram.exe",),
    "max": (r"%LOCALAPPDATA%\MAX\MAX.exe", r"%APPDATA%\MAX\MAX.exe"),
    "макс": (r"%LOCALAPPDATA%\MAX\MAX.exe", r"%APPDATA%\MAX\MAX.exe"),
    "ватсап": (r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",),
    "вотсап": (r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",),
    "whatsapp": (r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",),
    "discord": (r"%LOCALAPPDATA%\Discord\Discord.exe",),
    "дискорд": (r"%LOCALAPPDATA%\Discord\Discord.exe",),
    "teams": (r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe",),
    "тимс": (r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe",),
    "майкрософт teams": (r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe",),
    "microsoft teams": (r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe",),
    "вайбер": (r"%LOCALAPPDATA%\Viber\Viber.exe",),
    "viber": (r"%LOCALAPPDATA%\Viber\Viber.exe",),
}


def launch_paths(app):
    """Существующие пути запуска мессенджера. Пусто, если не нашли — не выдумываем.
    Нужно, потому что установки «для себя» (Telegram, MAX, WhatsApp, Discord) не в PATH."""
    out = []
    for pat in LAUNCH_PATHS.get(_norm(app), ()):
        path = os.path.expandvars(pat)
        if os.path.isfile(path):
            out.append(path)
    return out

# Родственники и частые обращения: то, что в именительном падеже совпадает с подписью чата
KIN = {"маме": "мама", "мамуле": "мама", "маму": "мама", "мамулю": "мама", "мамочке": "мама", "мамочку": "мама",
       "папе": "папа", "папуле": "папа", "папу": "папа", "папочке": "папа", "папулю": "папа",
       "брату": "брат", "сестре": "сестра", "сестру": "сестра", "бабушке": "бабушка", "бабуле": "бабушка",
       "бабушку": "бабушка", "дедушке": "дедушка", "дедуле": "дедушка", "дедушку": "дедушка",
       "жене": "жена", "жену": "жена", "мужу": "муж", "сыну": "сын", "дочке": "дочка", "дочери": "дочь",
       "дочку": "дочка", "подруге": "подруга", "другу": "друг"}

# «открой телеграм и напиши алексею привет», «открой max и напиши мамуле: привет», «…и отправь саше как дела»
MSG = re.compile(
    r"^(?:открой|открыть|запусти|запустить|зайди в|перейди в)\s+(?P<app>.+?)\s+(?:и|а затем|потом|затем)\s+"
    r"(?:напиши|напишите|отправь|отправьте|скажи)\s+(?P<who>[^\s:,]+)(?:\s*[:,]\s*|\s+)(?P<text>.+?)\s*$",
    re.IGNORECASE)


def _norm(s):
    return " ".join(str(s or "").lower().replace("ё", "е").split())


def parse(goal):
    """Фраза → {'app', 'who', 'text', 'candidates', 'search'} или None, если это не просьба написать в мессенджере."""
    m = MSG.match(" ".join(str(goal or "").split()))
    if not m:
        return None
    app = m.group("app").strip()
    if _norm(app) not in MESSENGERS:
        return None
    who = _norm(m.group("who"))
    text = m.group("text").strip(" :")
    if not who or not text:
        return None
    cands = candidates(who)
    return {"app": app, "who": who, "text": text[:400],
            "candidates": cands, "search": cands[0]}


def candidates(who):
    """Возможные подписи чата в именительном падеже — полные, самые вероятные первыми.
    «мамуле» → «мамуля» (близких подписывают так), потом «мамула», «мама» и само слово.
    Имя пишем полностью: обрезанное имя поиск не находит."""
    w = _norm(who)
    out = []
    base = ""
    if len(w) > 4 and w.endswith("ем"):                      # алексеем → алексей
        base = w[:-2]
    elif len(w) > 3 and w.endswith(("ю", "у", "е")):          # алексею → алексей, мамуле → мамуля, катю → катя
        base = w[:-1]
    elif len(w) > 3 and w.endswith(("ей", "ой")):             # с сашей → саша, с катей → катя
        base = w[:-2]
    if base:
        if base.endswith(("е", "и", "й")):
            out.append(base + "й")                           # алексе → алексей
        if base[-1:] in "жшчцкгх":
            out += [base + "а", base + "я"]                   # после шипящих и к/г/х пишется «а»: саша
        else:
            out += [base + "я", base + "а"]                   # мамуля, катя
        out.append(base + "ь")
        if w.endswith(("у", "ю")) and base[-1:] not in "аеёиоуыэюяйь":
            out.insert(0, base)                              # «ивану» → «иван», «антону» → «антон» (раньше такого имени среди вариантов не было)
    if w in KIN:
        out.append(KIN[w])                                   # «мамуле» → «мама» — если контакт подписан так
    out.append(w)
    seen, result = set(), []
    for c in out:
        if c and len(c) > 1 and c not in seen:
            seen.add(c)
            result.append(c)
    return result


def find_search_field(fields):
    """Поле поиска среди полей окна. None — не нашли, тогда имя пишем в фокус."""
    for f in fields or []:
        if SEARCH_FIELD.search(f or ""):
            return f
    return None


def _words(name):
    return re.findall(r"[а-я]+|[a-z]+", _norm(name))


def match_contact(cands, names):
    """Подпись чата, которая подходит к имени. Короткие подписи (сам чат) важнее строк сообщений
    вроде «Алексей привет». Нет подходящей — None."""
    names = [n for n in (names or []) if n and len(n) <= 80]
    names.sort(key=lambda n: (len(_words(n)), len(n)))
    for c in cands:                                             # 1) слово в подписи совпадает целиком
        for n in names:
            if c in _words(n):
                return n
    for c in cands:                                             # 2) похожее слово (опечатка, окончание)
        if len(c) < 4:
            continue
        for n in names:
            if any(difflib.SequenceMatcher(None, c, x).ratio() >= 0.85 for x in _words(n)[:2]):
                return n
    return None


MESSAGE_FIELD = re.compile(r"сообщ|message|написать|напишите|введите текст", re.IGNORECASE)
SEARCH_FIELD = re.compile(r"поиск|search|найти", re.IGNORECASE)


def find_message_field(fields):
    """Поле ввода сообщения среди полей окна по названию. None — не нашли, тогда текст вводим в фокус."""
    for f in fields or []:
        name = str(f or "")
        if MESSAGE_FIELD.search(name) and not SEARCH_FIELD.search(name):
            return name
    return None
