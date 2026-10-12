"""Команды Mico для Windows. Разбирает фразу и выполняет действие.
handle(q, notify, last_hwnd) -> Reply | None  (None — это не команда, пусть отвечает модель)."""
import difflib, json, os, re, subprocess, threading, time, webbrowser
from datetime import datetime, timedelta
from urllib.parse import quote

import context
import components
import winctl as W
from actions import Reply, reminder, sysinfo
from ru_text import normalize, translit

HOME = os.path.expanduser("~")
SEARCH_URL = "https://www.google.com/search?q="      # main.py подставит из настроек


class Ctx:
    def __init__(self, notify, last_hwnd):
        self.notify, self.last_hwnd = notify, last_hwnd


ON_RE = re.compile(r"\b(включи|включить|вруби|врубить|активируй|разреши|разрешить)\b")
OFF_RE = re.compile(r"\b(выключи|выключить|отключи|отключить|выруби|вырубить|деактивируй|запрети|запретить|"
                    r"останови|убери)\b")


def _has(ql, key):
    return re.search(r"(?<![\w-])" + re.escape(key), ql) is not None


def _fmt_dur(secs):
    h, rest = divmod(int(secs), 3600)
    m, s = divmod(rest, 60)
    return " ".join(p for p in (f"{h} ч" if h else "", f"{m} мин" if m else "", f"{s} сек" if s else "") if p)


# ============================ Подтверждение опасных действий ============================
_PENDING = {"fn": None, "until": 0.0}
_SHUTDOWN_UNTIL = [0.0]
YES = re.compile(r"\W*(да|ага|угу|давай|подтверждаю|конечно|выполняй|делай|yes)\W*(пожалуйста)?\W*")
NO = re.compile(r"\W*(нет|не надо|не нужно|не стоит|отмена|отмени|стоп|не делай|no)\W*")


def _ask(question, fn):
    _PENDING.update(fn=fn, until=time.time() + 30)
    return Reply(question + " Скажи «да» или «нет».", "worried")


def _pending(ql):
    if _PENDING["fn"] and time.time() < _PENDING["until"]:
        if YES.fullmatch(ql):
            fn, _PENDING["fn"] = _PENDING["fn"], None
            return fn()
        if NO.fullmatch(ql):
            _PENDING["fn"] = None
            return Reply("Хорошо, ничего не делаю 👌", "happy")
    _PENDING["fn"] = None if time.time() >= _PENDING["until"] else _PENDING["fn"]
    if time.time() < _SHUTDOWN_UNTIL[0] and (NO.fullmatch(ql) or re.search(r"отмени\w*\s+(выключен|перезагруз)", ql)):
        W.abort_shutdown()
        _SHUTDOWN_UNTIL[0] = 0
        return Reply("Остановил выключение ✋", "happy")
    return None


# ============================ Питание ============================
PC = r"(пк|компьютер|комп|ноутбук|систему|виндовс|windows)"


def _power(ql, ctx):
    if components.find_toggle(ql) or components.find_adjust(ql):      # «выключи windows управляет принтером» — не выключение ПК
        return None
    if re.search(rf"(выключи|выключить|выруби|вырубить|заверши|завершить)\s+(работу\s+)?{PC}|заверши(ть)?\s+работу|"
                 r"выключись", ql):
        def go():
            W.shutdown(False, 10)
            _SHUTDOWN_UNTIL[0] = time.time() + 12
            return Reply("Выключаю через 10 секунд. Передумал — скажи «отмена» 🌙", "sleepy")
        return _ask("Точно выключить компьютер?", go)
    if re.search(rf"перезагруз\w*\s+{PC}", ql) or re.fullmatch(r"\W*(перезагрузи(сь)?|перезагрузка|перезагрузить)"
                                                              r"(\s+пожалуйста)?\W*", ql):
        def go():
            W.shutdown(True, 10)
            _SHUTDOWN_UNTIL[0] = time.time() + 12
            return Reply("Перезагружаю через 10 секунд. Передумал — скажи «отмена» 🔄", "surprised")
        return _ask("Точно перезагрузить компьютер?", go)
    if re.search(r"выйди из (системы|учетной записи|аккаунта)|выход из системы|смени(ть)? пользователя", ql):
        return _ask("Выйти из учётной записи?", lambda: (W.sign_out(), Reply("Выходим 👋", "idle"))[1])
    if re.search(r"очисти\w*\s+корзину", ql):
        return _ask("Очистить корзину навсегда?",
                    lambda: Reply("Корзина очищена 🗑" if W.empty_recycle_bin() else "Не получилось очистить корзину",
                                  "happy"))
    if re.search(r"гибернац", ql):
        W.hibernate()
        return Reply("Гибернация 💤", "sleepy")
    if re.search(r"спящ\w*\s+режим|режим\s+сна|усыпи|засни|в\s+сон\b", ql):
        W.sleep_pc()
        return Reply("Перевожу ПК в сон 💤", "sleepy")
    if re.search(r"(заблокируй|заблокировать|блокировк\w*)(\s+(пк|компьютер|экран|систему))?\b", ql):
        W.lock()
        return Reply("Блокирую 🔒", "idle")
    if re.search(r"(выключи|погаси|отключи)\s+(экран|монитор|дисплей)", ql):
        W.monitor_off()
        return Reply("Гашу экран 🌑 (шевельни мышкой — включится)", "sleepy")
    m = re.search(r"режим\s+(производительност|высокой производительност|максимальной)|"
                  r"(экономн|энергосберегающ)\w*\s+(режим|план)|режим\s+(экономии|энергосбережен)|"
                  r"(сбалансированн)\w*\s+(режим|план)", ql)
    if m:
        key = "performance" if "производ" in ql or "максимал" in ql else "saver" if re.search(r"эконом|энергосб", ql) \
            else "balanced"
        ok = W.set_power_plan(key)
        names = {"performance": "высокая производительность ⚡", "saver": "экономия энергии 🍃",
                 "balanced": "сбалансированный ⚖️"}
        return Reply(f"Схема питания: {names[key]}" if ok else
                     "Не получилось сменить схему питания (возможно, её нет на этом ПК)", "happy" if ok else "worried")
    return None


# ============================ Таймеры и будильники ============================
_TIMERS = []


def _timer(ql, ctx):
    if re.search(r"(отмени|отключи|останови|убери|сбрось|выключи|удали)\w*\s+(все\s+)?(таймер|будильник)", ql):
        n = len(_TIMERS)
        for t in _TIMERS:
            t.cancel()
        _TIMERS.clear()
        return Reply(f"Отменил таймеры и будильники ({n}) ✅" if n else "Активных таймеров нет 🤷", "happy")
    if "будильник" in ql:
        m = re.search(r"(?:на|в)\s*(\d{1,2})(?:\s*[:.]?\s*(\d{2}))?\s*(утра|вечера|дня|ночи)?", ql)
        if not m:
            return Reply("Скажи так: «поставь будильник на 7:30» ⏰", "curious")
        h, mi, part = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        if part in ("вечера", "дня") and h < 12:
            h += 12
        if h > 23 or mi > 59:
            return Reply("Не поняла время будильника 🤔", "curious")
        now = datetime.now()
        when = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if when <= now:
            when += timedelta(days=1)
        _schedule((when - now).total_seconds(), ctx, f"будильник на {when:%H:%M} — пора!")
        return Reply(f"Будильник на {when:%H:%M} ({'завтра' if when.date() != now.date() else 'сегодня'}) ⏰ "
                     "Сработает, пока Mico запущен.", "happy")
    if "таймер" in ql:
        pairs = re.findall(r"(\d+)\s*(сек\w*|мин\w*|час\w*|ч\b)", ql)
        if not pairs:
            return Reply("На сколько поставить таймер? Например: «таймер на 10 минут» ⏳", "curious")
        secs = sum(int(n) * (1 if u.startswith("сек") else 60 if u.startswith("мин") else 3600) for n, u in pairs)
        if not 1 <= secs <= 86400:
            return Reply("Я умею таймеры от секунды до 24 часов ⏳", "curious")
        _schedule(secs, ctx, f"таймер на {_fmt_dur(secs)}: время вышло!")
        return Reply(f"Таймер на {_fmt_dur(secs)} запущен ⏳ Скажу, когда время выйдет (пока Mico запущен).", "happy")
    return None


def _schedule(secs, ctx, text):
    def fire():
        if t in _TIMERS:
            _TIMERS.remove(t)
        ctx.notify(text)
    t = threading.Timer(secs, fire)
    t.daemon = True
    _TIMERS.append(t)
    t.start()


# ============================ Сайты и поиск ============================
SITES = {"ютуб": "youtube.com", "youtube": "youtube.com", "гугл": "google.com", "google": "google.com",
         "яндекс": "yandex.ru", "yandex": "yandex.ru", "вк": "vk.com", "вконтакте": "vk.com", "vk": "vk.com",
         "гитхаб": "github.com", "github": "github.com", "википедия": "ru.wikipedia.org",
         "wikipedia": "wikipedia.org", "эппл": "apple.com", "apple": "apple.com", "амазон": "amazon.com",
         "amazon": "amazon.com", "нетфликс": "netflix.com", "netflix": "netflix.com", "твиттер": "x.com",
         "фейсбук": "facebook.com", "facebook": "facebook.com", "инстаграм": "instagram.com",
         "instagram": "instagram.com", "линкедин": "linkedin.com", "реддит": "reddit.com", "habr": "habr.com",
         "хабр": "habr.com", "озон": "ozon.ru", "ozon": "ozon.ru", "вайлдберриз": "wildberries.ru",
         "авито": "avito.ru", "avito": "avito.ru", "почта": "mail.google.com", "джимейл": "mail.google.com",
         "gmail": "mail.google.com", "чатгпт": "chatgpt.com", "chatgpt": "chatgpt.com", "клод": "claude.ai",
         "claude": "claude.ai", "майкрософт": "microsoft.com", "microsoft": "microsoft.com", "твитч": "twitch.tv",
         "twitch": "twitch.tv", "спотифай": "open.spotify.com", "тикток": "tiktok.com", "телеграм веб": "web.telegram.org",
         "кинопоиск": "kinopoisk.ru", "мейл": "mail.ru", "яндекс почта": "mail.yandex.ru", "гугл карты": "maps.google.com",
         "гугл диск": "drive.google.com", "гугл переводчик": "translate.google.com"}
SITE_BASE = {k: v.split(".")[-2] for k, v in SITES.items() if " " not in k}
TLD = {"ком": "com", "ру": "ru", "орг": "org", "нет": "net", "инфо": "info", "ио": "io", "ай": "ai",
       "эпп": "app", "дев": "dev", "ус": "us", "юк": "uk", "бай": "by", "юа": "ua", "кз": "kz", "рф": "рф"}
LATIN = re.compile(r"[a-z0-9-]+")


def site_url(text):
    """'apple.com' / 'эппл точка ком' / 'ютуб' -> https-ссылка или None."""
    t = text.strip(" .!?\"'«»")
    if re.match(r"https?://\S+$", t):
        return t
    if re.fullmatch(r"(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:/\S*)?", t):
        return "https://" + t
    if t in SITES:
        return "https://" + SITES[t]
    t2 = re.sub(r"\s*\bточка\b\s*", ".", t)
    if "." in t2:
        labels = t2.replace(" ", "").split(".")
        base = SITE_BASE.get(labels[0], labels[0] if LATIN.fullmatch(labels[0]) else None)
        tld = TLD.get(labels[-1], labels[-1] if LATIN.fullmatch(labels[-1]) else None)
        if base and tld and len(labels) == 2:
            return f"https://{base}.{tld}"
    return None


def _websearch(ql, ctx):
    m = (re.search(r"\b(?:загугли|погугли|нагугли)\s+(.+)", ql) or
         re.search(r"\b(?:найди|поищи|ищи)\s+(?:в\s+(?:интернете|сети|гугле|яндексе|браузере)\s+)(.+)", ql) or
         re.search(r"\b(?:найди|поищи|ищи)\s+(.+?)\s+в\s+(?:интернете|сети|гугле|яндексе|браузере)\b", ql))
    if not m:
        return None
    q = m.group(1).strip(" .!?")
    webbrowser.open(SEARCH_URL + quote(q))
    return Reply(f"Ищу в интернете: «{q}» 🔎", "curious")


# ============================ Страницы настроек Windows ============================
SETTINGS = [
    (("wi-fi", "wifi", "wi fi", "вай"), "network-wifi", "Wi-Fi"),
    (("bluetooth", "блютуз", "блютус"), "bluetooth", "Bluetooth"),
    (("режим полет", "авиарежим", "в самолет"), "network-airplanemode", "Режим полёта"),
    (("хот-спот", "хотспот", "точка доступа", "мобильный хот"), "network-mobilehotspot", "Мобильный хот-спот"),
    (("vpn", "впн"), "network-vpn", "VPN"),
    (("прокси",), "network-proxy", "Прокси"),
    (("ethernet", "проводн"), "network-ethernet", "Ethernet"),
    (("сеть", "интернет", "подключени"), "network-status", "Сеть и интернет"),
    (("ночной свет", "ночной режим"), "nightlight", "Ночной свет"),
    (("экономия заряда", "экономия батаре", "экономии заряда"), "batterysaver", "Экономия заряда"),
    (("не беспокоить", "фокус", "уведомлен"), "notifications", "Уведомления"),
    (("геолокац", "местоположен"), "privacy-location", "Местоположение"),
    (("камер",), "privacy-webcam", "Доступ к камере"),
    (("экран", "дисплей", "разрешение", "масштаб", "монитор"), "display", "Экран"),
    (("звук", "динамик", "громкост"), "sound", "Звук"),
    (("батаре", "питани", "сон"), "powersleep", "Питание и батарея"),
    (("хранилищ", "диск", "очистк"), "storagesense", "Хранилище"),
    (("обновлен", "update"), "windowsupdate", "Центр обновления Windows"),
    (("восстановлен", "сброс"), "recovery", "Восстановление"),
    (("активац",), "activation", "Активация"),
    (("резервн", "архиваци"), "backup", "Резервное копирование"),
    (("устранение неполад", "диагностик"), "troubleshoot", "Устранение неполадок"),
    (("по умолчанию",), "defaultapps", "Приложения по умолчанию"),
    (("автозагрузк", "автозапуск"), "startupapps", "Автозагрузка"),
    (("приложен", "программ"), "appsfeatures", "Приложения"),
    (("дополнительные компоненты",), "optionalfeatures", "Дополнительные компоненты"),
    (("экран блокировки",), "lockscreen", "Экран блокировки"),
    (("обои", "фон"), "personalization-background", "Фон"),
    (("цвет", "акцент"), "colors", "Цвета"),
    (("тема", "оформлен", "персонализ"), "personalization", "Персонализация"),
    (("шрифт",), "fonts", "Шрифты"),
    (("панель задач",), "taskbar", "Панель задач"),
    (("конфиденц", "приватн"), "privacy", "Конфиденциальность"),
    (("язык", "раскладк", "регион", "клавиатур"), "regionlanguage", "Язык и регион"),
    (("дата", "время", "часовой пояс"), "dateandtime", "Дата и время"),
    (("мышь", "мышк"), "mousetouchpad", "Мышь"),
    (("тачпад",), "devices-touchpad", "Сенсорная панель"),
    (("принтер", "сканер"), "printers", "Принтеры и сканеры"),
    (("устройства", "usb"), "connecteddevices", "Устройства"),
    (("ввод текста", "автозамен"), "typing", "Ввод текста"),
    (("буфер обмена",), "clipboard", "Буфер обмена"),
    (("многозадачност",), "multitasking", "Многозадачность"),
    (("проецирован", "второй экран"), "project", "Проецирование"),
    (("удаленный рабочий стол",), "remotedesktop", "Удалённый рабочий стол"),
    (("о системе", "характеристик"), "about", "О системе"),
    (("специальные возможности", "доступност"), "easeofaccess", "Специальные возможности"),
    (("игровой режим",), "gaming-gamemode", "Игровой режим"),
    (("игровая панель", "game bar"), "gaming-gamebar", "Игровая панель"),
    (("учетн", "аккаунт", "профиль"), "yourinfo", "Ваши данные"),
    (("вход в систему", "пин-код", "windows hello"), "signinoptions", "Параметры входа"),
    (("разработчик",), "developers", "Для разработчиков"),
]


def settings_page(ql):
    for keys, uri, title in SETTINGS:
        if any(_has(ql, k) for k in keys):
            return "ms-settings:" + uri, title
    return None


# ============================ Переключатели Windows ============================
def _remember_toggle(t, want):
    context.remember("toggle", repeat=lambda: _toggle_do(t, want), undo=lambda: _toggle_do(t, not want),
                     want=want, name=t.name)


def _toggle_do(t, want):
    if t.page:
        os.startfile("ms-settings:" + t.page)
        return Reply(f"«{t.name}» Windows не даёт переключать из программ — открыл нужную страницу ⚙️", "happy")
    if t.combo:
        W.press(*t.combo)
        return Reply(f"{t.name}: нажал {'+'.join(c.upper() for c in t.combo)} ⌨️", "happy")
    if t.proc:
        if want:
            subprocess.Popen(["cmd", "/c", "start", "", t.proc], creationflags=W.NOWIN)
        else:
            W.run_quiet("taskkill", "/IM", t.proc, "/F")
        return Reply(f"{t.name}: {'включено' if want else 'выключено'} ✅", "happy")
    try:
        ok, msg = t.fn(want)
    except Exception as e:
        ok, msg = False, str(e)
    if not ok:
        hint = msg or ("нужны права администратора" if t.admin else "Windows отказала")
        return Reply(f"{t.name}: не получилось ({hint}) 😔", "sad")
    _remember_toggle(t, want)
    note = t.note if t.note and (want or not t.note_on_only) else ""
    return Reply(f"{t.name} — {'включено' if want else 'выключено'} ✅" + (f" {note}" if note else ""), "happy")


def _toggles(ql, ctx):
    on, off = ON_RE.search(ql), OFF_RE.search(ql)
    if not (on or off):
        return None
    t = components.find_toggle(ql)
    if t is None:
        return None
    want = bool(on) and (not off or on.start() < off.start())
    question = t.confirm_on if want else t.confirm_off
    if question:
        return _ask(question, lambda: _toggle_do(t, want))
    return _toggle_do(t, want)


DANGER = re.compile(r"сбрось\s+(сеть|сетевые)|сброс\s+сети|\bsfc\b|целостност")


def _run_sys(text, fn):
    ok, msg = fn()
    return Reply(text if ok else f"Не получилось: {msg or 'Windows отказала'} 😔", "happy" if ok else "sad")


def _system(ql, ctx):
    for pat, text, fn in components.ACTIONS:
        if re.search(pat, ql):
            if re.search(r"буфер", ql) and re.search(r"очисти|почисти", ql):
                return _ask("Очистить историю буфера обмена? Закреплённые элементы останутся.",
                            lambda: _run_sys(text, fn))
            if DANGER.search(ql):
                return _ask("Это может занять время и изменить сетевые настройки или системные файлы.",
                            lambda: _run_sys(text, fn))
            return _run_sys(text, fn)
    return None


# ============================ Ссылки по теме ============================
LINKS_RE = re.compile(r"^(?:открой|покажи|дай|найди|поищи)\s+(?:мне\s+)?(?:ссылки|ссылку|справку|инструкци\w*|статьи|статью)"
                      r"\s*(?:по\s+теме\s+|по\s+|о\s+|про\s+|для\s+)?(.+)$|"
                      r"^(?:ссылки|справка|инструкция)\s+(?:по\s+теме\s+|по\s+|о\s+|про\s+|для\s+)?(.+)$")


def _links(ql, ctx):
    """«открой ссылки по теме блютуз» / «справка по брандмауэру»: ищет официальные статьи Microsoft по теме."""
    m = LINKS_RE.search(ql.strip(" .!?"))
    if not m:
        return None
    topic = (m.group(1) or m.group(2) or "").strip(" .!?")
    if not topic:
        return Reply("По какой теме? Например: «открой ссылки по теме блютуз» 🔗", "curious")
    t = components.find_toggle(topic)
    name = t.name if t else (settings_page(topic) or (None, topic))[1]
    query = f"{name} Microsoft инструкция" + ("" if "windows" in name.lower() else " Windows 11")
    webbrowser.open(SEARCH_URL + quote(query))
    return Reply(f"Открыл поиск официальных статей по теме «{name}» 🔗 Если нужна страница настроек — скажи «открой настройки {name}».",
                 "happy")


def _followup(ql, ctx):
    """Короткие продолжения по памяти последнего действия: «дальше», «ещё», «назад», «а блютуз?»."""
    last = context.last()
    if not last:
        return None
    if context.is_repeat(ql):
        return last["repeat"]() if last.get("repeat") else None
    if context.is_undo(ql):
        return last["undo"]() if last.get("undo") else None
    m = re.fullmatch(r"а\s+(.+)", context.bare(ql))
    if m and last["kind"] == "toggle" and not (ON_RE.search(ql) or OFF_RE.search(ql)):
        t = components.find_toggle(m.group(1))
        if t:
            return _toggle_do(t, last["want"])
    return None


# ============================ Громкость, яркость, тема, медиа ============================
def _vol_abs(n):
    prev = W.get_volume()
    v = W.set_volume(n)
    if v is None:
        return Reply("Не смог выставить точную громкость (установи pycaw: pip install pycaw comtypes) 😔", "sad")
    context.remember("volume", repeat=lambda: _vol_abs(n),
                     undo=(lambda: _vol_abs(prev)) if prev is not None else None)
    return Reply(f"Громкость {v}% 🔊", "happy")


def _vol_delta(d):
    v = W.change_volume(d)
    context.remember("volume", repeat=lambda: _vol_delta(d), undo=lambda: _vol_delta(-d))
    word = "громче 🔊" if d > 0 else "тише 🔉"
    return Reply(f"Сделал {word}{f' — {v}%' if v is not None else ''}", "happy")


def _bright_abs(n):
    prev = W.get_brightness()
    v = W.set_brightness(n)
    if v is None:
        return Reply("Не получилось (яркость программно меняется на ноутбуках и совместимых мониторах) 😔", "sad")
    context.remember("bright", repeat=lambda: _bright_abs(n),
                     undo=(lambda: _bright_abs(prev)) if prev is not None else None)
    return Reply(f"Яркость {v}% 🔆", "happy")


def _bright_delta(d):
    cur = W.get_brightness()
    if cur is None:
        return Reply("Не вижу управляемой яркости — на настольных мониторах её меняют кнопками монитора 🖥", "sad")
    v = W.set_brightness(cur + d)
    context.remember("bright", repeat=lambda: _bright_delta(d), undo=lambda: _bright_delta(-d))
    return Reply(f"Яркость {v}% 🔆" if v is not None else "Не получилось 😔", "happy" if v is not None else "sad")


MEDIA_TEXT = {"next": "⏭ Следующий трек", "prev": "⏮ Предыдущий трек", "play": "⏯ Готово"}
MEDIA_UNDO = {"next": "prev", "prev": "next"}


def _media(kind):
    W.press(kind)
    undo = MEDIA_UNDO.get(kind)
    context.remember("media", repeat=lambda: _media(kind), undo=(lambda: _media(undo)) if undo else None)
    return Reply(MEDIA_TEXT[kind], "happy")


def _audio_screen(ql, ctx):
    m = re.search(r"(?:громкост\w*|звук\w*)\D{0,12}?(\d{1,3})\b", ql)
    if m and not re.search(r"\b(выключи|включи|отключи)\s+звук", ql):
        return _vol_abs(int(m.group(1)))
    if re.search(r"(громкост|звук)\w*.*\b(максимум|максимальн|полн)", ql):
        return _vol_abs(100)
    if re.search(r"(громкост|звук)\w*.*\bминимум", ql):
        return _vol_abs(5)
    if re.search(r"(громкост|звук)\w*.*\bполовин", ql):
        return _vol_abs(50)
    big = 25 if re.search(r"намного|сильно|гораздо|значительно", ql) else 10
    if re.search(r"\b(по)?громче\b|(прибавь|увеличь|добавь)\s+(звук|громкость)", ql):
        return _vol_delta(big)
    if re.search(r"\b(по)?тише\b|(убавь|уменьши|убери)\s+(звук|громкость)", ql):
        return _vol_delta(-big)
    if re.search(r"без звука|выключи звук|отключи звук|\bmute\b|заглуши", ql):
        W.set_mute(True)
        return Reply("Звук выключен 🔇", "happy")
    if re.search(r"включи звук|верни звук|размуть|со звуком", ql):
        W.set_mute(False)
        return Reply("Звук включён 🔊", "happy")
    # яркость
    m = re.search(r"яркост\w*\D{0,15}(\d{1,3})\b", ql)
    target = int(m.group(1)) if m else (100 if re.search(r"яркост\w*.*(максимум|максимальн|полн)", ql) else
                                        5 if re.search(r"яркост\w*.*минимум", ql) else
                                        50 if re.search(r"яркост\w*.*половин", ql) else None)
    delta = (20 if re.search(r"\bярче\b|\bпояркее\b|(прибавь|увеличь|добавь)\s+яркость", ql) else
             -20 if re.search(r"\bтемнее\b|\bпотемнее\b|(убавь|уменьши)\s+яркость|приглуши", ql) else 0)
    if target is not None:
        return _bright_abs(target)
    if delta:
        return _bright_delta(delta)
    # тема Windows
    dark = re.search(r"темн\w*\s+(тем|режим|оформлен)|(тем|режим)\w*\s+темн", ql)
    light = re.search(r"светл\w*\s+(тем|режим|оформлен)|(тем|режим)\w*\s+светл", ql)
    if dark or light:
        off = bool(OFF_RE.search(ql))
        want_light = bool(light) != off if light else off
        W.set_theme(want_light)
        return Reply("Включил светлую тему ☀️" if want_light else "Включил тёмную тему 🌙", "happy")
    # медиа
    if re.search(r"\bпауза\b|на паузу|останови\s+(музыку|видео|воспроизведение|песню)|продолжи\s+(музыку|видео|воспроизведение)|"
                 r"возобнови", ql):
        return _media("play")
    if re.search(r"следующ\w*\s+(трек|песн\w*|композици\w*|видео)|переключи\s+(трек|песню)", ql):
        return _media("next")
    if re.search(r"предыдущ\w*\s+(трек|песн\w*|композици\w*)|прошл\w*\s+(трек|песн\w*)", ql):
        return _media("prev")
    return None


# ============================ Окна и рабочие столы ============================
def _refocus(ctx):
    """Если сейчас в фокусе окно самого Mico — вернуть фокус на последнее пользовательское окно."""
    try:
        import win32gui, win32process
        fg = win32gui.GetForegroundWindow()
        if win32process.GetWindowThreadProcessId(fg)[1] == os.getpid():
            h = ctx.last_hwnd()
            if h and win32gui.IsWindow(h):
                W.focus(h)
                time.sleep(0.15)
    except Exception:
        pass


def _window_cmd(ctx, cmd):
    h = ctx.last_hwnd()
    if not h:
        return False
    W.show_window(h, cmd)
    return True


ALIASES_PROC = {"блокнот": "notepad", "калькулятор": "calculator", "хром": "chrome", "chrome": "chrome",
                "эдж": "msedge", "edge": "msedge", "firefox": "firefox", "фаерфокс": "firefox", "файрфокс": "firefox",
                "опера": "opera", "opera": "opera", "телеграм": "telegram", "telegram": "telegram",
                "дискорд": "discord", "discord": "discord", "спотифай": "spotify", "spotify": "spotify",
                "стим": "steam", "steam": "steam", "ворд": "winword", "word": "winword", "эксель": "excel",
                "excel": "excel", "пауэрпоинт": "powerpnt", "powerpoint": "powerpnt",
                "paint": "mspaint", "пейнт": "mspaint", "проводник": "explorer", "диспетчер задач": "taskmgr",
                "терминал": "windowsterminal", "командная строка": "cmd", "настройки": "systemsettings"}


def _app_tokens(name):
    name = name.strip(" .!?")
    toks = [ALIASES_PROC.get(name), name, translit(name)]
    for k, v in ALIASES_PROC.items():
        if k in name:
            toks.append(v)
    return [t for t in toks if t and len(t) >= 3]


def _windows(ql, ctx):
    if re.search(r"(сверни|свернуть|убери)\s+все(\s+окна)?|покажи\s+рабочий\s+стол", ql):
        W.press("win", "d")
        return Reply("Свернул всё, вот рабочий стол 🖥", "happy")
    if re.search(r"(создай|новый|открой новый|добавь)\s+(виртуальный\s+)?рабочий\s+стол", ql):
        W.press("win", "ctrl", "d")
        return Reply("Новый рабочий стол создан 🪟", "happy")
    if re.search(r"(следующий|на следующий|вперед на)\s+рабочий\s+стол", ql):
        W.press("win", "ctrl", "right")
        return Reply("Перешёл на следующий рабочий стол ➡️", "happy")
    if re.search(r"(предыдущий|на предыдущий|назад на)\s+рабочий\s+стол", ql):
        W.press("win", "ctrl", "left")
        return Reply("Перешёл на предыдущий рабочий стол ⬅️", "happy")
    if re.search(r"закрой\s+(этот\s+)?(виртуальный\s+)?рабочий\s+стол", ql):
        W.press("win", "ctrl", "f4")
        return Reply("Закрыл рабочий стол", "happy")
    if re.search(r"покажи\s+все\s+(окна|задачи|приложения)|обзор задач|представление задач|task view", ql):
        W.press("win", "tab")
        return Reply("Показываю все окна 🗂", "happy")
    if re.search(r"(переключи(сь)?|смени|перейди)\s+(на\s+)?(следующ\w*\s+|друг\w*\s+|предыдущ\w*\s+)?"
                 r"(задач\w*|окн\w*|приложени\w*)\W*$|следующ\w*\s+(задач\w*|окн\w*)|alt tab", ql):
        W.press("alt", "tab")
        return Reply("Переключил окно 🔀", "happy")
    m = re.search(r"переключи(?:сь)?\s+(?:на|в)\s+(.+)", ql)
    if m:
        name = m.group(1).strip(" .!?")
        wins = W.find_windows(_app_tokens(name))
        if wins and W.focus(wins[0][0]):
            return Reply(f"Переключился на «{wins[0][1][:50]}» 🔀", "happy")
        return Reply(f"Не нашёл открытое окно «{name}» 🤔", "sad")
    if re.search(r"(переключи|смени|поменяй)\s+(раскладку|язык)(\s+ввода)?|смени\s+язык", ql):
        W.press("win", "space")
        return Reply("Переключил раскладку ⌨️", "happy")
    if re.search(r"(вырежи|выдели|сними)\s+область|скриншот области|ножницы для области", ql):
        W.press("win", "shift", "s")
        return Reply("Выдели область экрана мышкой ✂️", "happy")
    if re.search(r"(открой|покажи)\s+(историю\s+буфера|буфер обмена)\b|история буфера обмена", ql):
        W.press("win", "v")
        return Reply("Открыл историю буфера (Win+V) 📋", "happy")
    if re.search(r"(прикрепи|прижми|поставь)\s+окно\s+(слева|налево)|окно\s+налево", ql):
        _refocus(ctx)
        W.press("win", "left")
        return Reply("Окно слева ⬅️", "happy")
    if re.search(r"(прикрепи|прижми|поставь)\s+окно\s+(справа|направо)|окно\s+направо", ql):
        _refocus(ctx)
        W.press("win", "right")
        return Reply("Окно справа ➡️", "happy")
    if re.search(r"(сверни|свернуть)(\s+(это|текущее|активное))?(\s+окно)?\W*$", ql):
        return Reply("Свернул окно ⬇️" if _window_cmd(ctx, 6) else "Не вижу окна, которое можно свернуть 🤔", "happy")
    if re.search(r"(разверни|развернуть)(\s+(это|текущее|активное))?(\s+окно)?(\s+на весь экран)?\W*$", ql):
        return Reply("Развернул окно ⬆️" if _window_cmd(ctx, 3) else "Не вижу окна, которое можно развернуть 🤔", "happy")
    if re.search(r"(восстанови|верни)\s+окно", ql):
        return Reply("Вернул окно ↕️" if _window_cmd(ctx, 9) else "Не вижу окна 🤔", "happy")
    if re.search(r"(закрой|закрыть)\s+(это\s+|текущее\s+|активное\s+)?окно\W*$", ql):
        h = ctx.last_hwnd()
        if not h:
            return Reply("Не вижу окна, которое можно закрыть 🤔", "sad")
        W.close_window(h)
        return Reply("Закрываю окно ❎", "happy")
    return None


# ============================ Приложения ============================
APPS = {"блокнот": "notepad", "калькулятор": "calc", "проводник": "explorer", "paint": "mspaint",
        "пейнт": "mspaint", "диспетчер задач": "taskmgr", "диспетчер устройств": "devmgmt.msc",
        "управление дисками": "diskmgmt.msc", "службы": "services.msc", "монитор ресурсов": "resmon",
        "сведения о системе": "msinfo32", "редактор реестра": "regedit", "командная строка": "cmd",
        "командн": "cmd", "терминал": "wt", "powershell": "powershell", "панель управления": "control",
        "ножницы": "snippingtool", "экранная клавиатура": "osk", "лупа": "magnify",
        "edge": "msedge", "эдж": "msedge", "гугл хром": "chrome", "chrome": "chrome", "хром": "chrome",
        "firefox": "firefox", "фаерфокс": "firefox", "файрфокс": "firefox", "опера": "opera",
        "word": "winword", "ворд": "winword", "excel": "excel", "эксель": "excel", "powerpoint": "powerpnt",
        "пауэрпоинт": "powerpnt", "vs code": "code",
        "часы": "ms-clock:", "будильник": "ms-clock:",
        "камера": "microsoft.windows.camera:", "фото": "ms-photos:", "карты": "bingmaps:",
        "магазин": "ms-windows-store:", "погода": "msnweather:", "xbox": "xbox:", "заметки": "ms-stickynotes:"}
_APP_KEYS = sorted(APPS, key=len, reverse=True)
FOLDERS = {"загрузк": "Downloads", "документ": "Documents", "рабочий стол": "Desktop", "изображен": "Pictures",
           "картинк": "Pictures", "музык": "Music", "видео": "Videos"}
SPECIAL = {"корзин": "shell:RecycleBinFolder", "этот компьютер": "shell:MyComputerFolder",
           "мой компьютер": "shell:MyComputerFolder"}
START_DIRS = [os.path.join(os.environ.get("ProgramData", ""), r"Microsoft\Windows\Start Menu\Programs"),
              os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")]
_START = []
_START_LOCK = threading.Lock()


def start_apps():
    """Все приложения из меню «Пуск» (включая Microsoft Store): [(имя, AppID)]. Кэшируется."""
    with _START_LOCK:
        if not _START:
            ok, out = W.ps("Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress", 40)
            try:
                data = json.loads(out)
                data = [data] if isinstance(data, dict) else data
                _START.extend((d["Name"], d["AppID"]) for d in data if d.get("Name") and d.get("AppID"))
            except Exception:
                pass
        return list(_START)


def warmup():
    threading.Thread(target=start_apps, daemon=True).start()


def _find_start_app(name):
    n, lat = name.lower(), translit(name)
    best, best_s = None, 0.0
    for nm, aid in start_apps():
        low = nm.lower()
        if len(n) >= 3 and (n in low or lat in low):
            s = 0.9 + 0.1 * (1 - min(len(low), 60) / 60)
        else:
            s = max(difflib.SequenceMatcher(None, n, low).ratio(), difflib.SequenceMatcher(None, lat, low).ratio())
        if s > best_s:
            best, best_s = (nm, aid), s
    return best if best_s >= 0.8 else None


def _launch(cmd):
    if cmd.endswith(":") or cmd.startswith(("ms-", "shell:", "http")):
        os.startfile(cmd)
    else:
        subprocess.Popen(["cmd", "/c", "start", "", cmd], creationflags=W.NOWIN)


FILLER = re.compile(r"^(пожалуйста\s+|мне\s+|программу\s+|приложение\s+|программы\s+|страницу\s+|вкладку\s+|"
                    r"папку\s+|в\s+браузере\s+)+")


def _open_item(item, strict=False):
    """Открыть одну цель. Возвращает (название, ok) либо None, если цель не распознана."""
    item = FILLER.sub("", item.strip(" .!?"))
    if not item:
        return None
    count = 1
    m = re.match(r"(\d)\s+(.+)", item)
    if m and 1 < int(m.group(1)) <= 5:
        count, item = int(m.group(1)), m.group(2)
    is_site = item.startswith("сайт ")
    if is_site:
        item = item[5:].strip()
    url = site_url(item)
    if url:
        webbrowser.open(url)
        return url.split("//", 1)[-1], True
    if is_site:
        webbrowser.open(SEARCH_URL + quote(item))
        return f"поиск «{item}»", True
    if item in ("браузер", "интернет"):
        webbrowser.open("about:blank")
        return "браузер", True
    m = None if strict else re.match(r"(?:локальный\s+)?диск\s+([a-zа-я])\b", item)
    if m:
        letter = {"с": "c", "д": "d", "е": "e", "ф": "f"}.get(m.group(1), m.group(1)).upper()
        os.startfile(f"{letter}:\\")
        return f"диск {letter}:", True
    for k, uri in ({} if strict else SPECIAL).items():
        if item.startswith(k):
            os.startfile(uri)
            return k, True
    for k, d in ({} if strict else FOLDERS).items():
        if item.startswith(k) or (k in item and len(item.split()) <= 2):
            os.startfile(os.path.join(HOME, d))
            return f"папка «{item}»", True
    if "настройк" in item or "параметр" in item:
        sp = settings_page(item)
        os.startfile(sp[0] if sp else "ms-settings:")
        return f"настройки: {sp[1] if sp else 'Windows'}", True
    for k in _APP_KEYS:
        if k in item:
            for _ in range(count):
                _launch(APPS[k])
            return item, True
    if item in SITES:
        webbrowser.open("https://" + SITES[item])
        return item, True
    hit = _find_start_app(item)
    if hit:
        for _ in range(count):
            os.startfile("shell:AppsFolder\\" + hit[1])
        return hit[0], True
    for base in START_DIRS:
        for dp, _, fn in os.walk(base):
            for f in fn:
                if f.lower().endswith(".lnk") and item in f.lower():
                    os.startfile(os.path.join(dp, f))
                    return f[:-4], True
    sp = settings_page(item)
    if sp:
        os.startfile(sp[0])
        return f"настройки: {sp[1]}", True
    return item, False


OPEN_RE = re.compile(r"\b(открой|открыть|запусти|запустить|включи|зайди на|зайди в|перейди на|перейди в|"
                     r"давай откроем)\s+(.+)$")
SPLIT_ITEMS = re.compile(r"\s*,\s*|\s+и\s+|\s+а также\s+|\s+плюс\s+|\s*&\s*")


# ============================ Музыка: любой сервис, а не только один ============================
MUSIC_SERVICES = [  # (название, как его называют, имя приложения в меню «Пуск» или None, сайт)
    ("Spotify", ("спотифай", "спотифи", "спотик", "spotify"), "Spotify", "https://open.spotify.com"),
    ("Яндекс Музыка", ("яндекс музык", "яндекс мьюзик", "yandex music"), "Яндекс Музыка", "https://music.yandex.ru"),
    ("SoundCloud", ("саунд клауд", "саундклауд", "саунд клоуд", "саунд кладу", "саундклоуд", "soundcloud"),
     "SoundCloud", "https://soundcloud.com"),
    ("Apple Music", ("эпл музык", "эппл музык", "эпл мьюзик", "apple music"), "Apple Music", "https://music.apple.com"),
    ("YouTube Music", ("ютуб музык", "ютьюб музык", "youtube music"), None, "https://music.youtube.com"),
    ("VK Музыка", ("вк музык", "вконтакте музык", "вк мьюзик", "vk music"), None, "https://vk.com/audio"),
    ("Deezer", ("deezer", "дизер"), "Deezer", "https://www.deezer.com"),
]
GENERIC_MUSIC = re.compile(r"\b(?:включи|запусти|открой|поставь|врубай|играй|давай)\s+(?:мне\s+|какую-нибудь\s+|"
                           r"что-нибудь\s+|любую\s+|нашу\s+|мою\s+)?(?:музык\w*|песн\w*|плейлист\w*|трек\w*)\b")


def _mentions(ql, aliases):
    """Есть ли в фразе название сервиса, в том числе с опечаткой («саунд кладу»)."""
    for a in aliases:
        if a in ql:
            return True
        n = len(a)
        for i in range(0, max(1, len(ql) - n + 1)):
            if difflib.SequenceMatcher(None, ql[i:i + n], a).ratio() >= 0.85:
                return True
    return False


def _start_app(name):
    hit = _find_start_app(name)
    if hit:
        os.startfile("shell:AppsFolder\\" + hit[1])
        return hit[0]
    return None


def _play_service(svc):
    name, _, app, site = svc
    if app and _start_app(app):
        return Reply(f"Открываю {name} 🎵", "happy")
    webbrowser.open(site)
    return Reply(f"{name} не установлен — открыл в браузере 🎵", "happy")


def _music(ql, ctx):
    named = next((s for s in MUSIC_SERVICES if _mentions(ql, s[1])), None)
    if named:
        return _play_service(named)
    if not GENERIC_MUSIC.search(ql):
        return None
    for svc in MUSIC_SERVICES:
        if svc[2] and _start_app(svc[2]):
            return Reply(f"Включаю музыку в {svc[0]} 🎵", "happy")
    webbrowser.open(MUSIC_SERVICES[1][3])
    return Reply("Музыкального приложения не нашёл, открыл Яндекс Музыку в браузере 🎵. "
                 "Можешь назвать сервис, например «включи музыку в саунд клауде».", "happy")


def _open_close(ql, ctx):
    m = OPEN_RE.search(ql)
    if m:
        strict = m.group(1) == "включи"
        rest = m.group(2)
        items = [i for i in SPLIT_ITEMS.split(rest) if i.strip()]
        done, failed = [], []
        for it in items:
            r = _open_item(it, strict)
            if r is None:
                continue
            (done if r[1] else failed).append(r[0])
        if strict and not done:
            return None
        if not done and not failed:
            return None
        parts = []
        if done:
            parts.append("Открываю: " + ", ".join(done) + " 🚀")
        if failed:
            parts.append("Не нашёл: " + ", ".join(f"«{f}»" for f in failed) + " 🤔")
        return Reply("\n".join(parts), "happy" if done else "sad")
    m = re.search(r"\b(закрой|закрыть)\s+(?!окно)(.+)$", ql)
    if m:
        closed, missing = [], []
        for it in [i for i in SPLIT_ITEMS.split(m.group(2)) if i.strip()]:
            name = FILLER.sub("", it.strip(" .!?"))
            wins = W.find_windows(_app_tokens(name))
            for w in wins:
                W.close_window(w[0])
            (closed if wins else missing).append(name)
        parts = []
        if closed:
            parts.append("Закрываю: " + ", ".join(closed) + " ❎")
        if missing:
            parts.append("Не нашёл открытых окон: " + ", ".join(f"«{x}»" for x in missing) + " 🤔")
        return Reply("\n".join(parts), "happy" if closed else "sad")
    return None


def _toggle_fallback(ql, ctx):
    """«включи/выключи X», где X — неизвестный переключатель: хотя бы открыть нужный раздел настроек."""
    if not (ON_RE.search(ql) or OFF_RE.search(ql)):
        return None
    sp = settings_page(ql)
    if sp:
        os.startfile(sp[0])
        return Reply(f"Прямого переключателя для этого нет — открыл раздел «{sp[1]}» ⚙️", "happy")
    names = components.suggest(ql)
    if names:
        return Reply("Не знаю такого переключателя. Возможно, ты имел в виду: "
                     + ", ".join(f"«{n}»" for n in names) + "? 🤔", "curious")
    return None


# ============================ Регулировка значений и информация о настройках ============================
import settings_info
ADJ_VERB = re.compile(r"\b(поставь|поставить|установи|установить|выстав\w*|сделай|задай|задать|настрой|настроить|"
                      r"измени\w*|поменяй|поменять|верни|вернуть)\b")
ADJ_UP = re.compile(r"\b(больше|выше|быстрее|побыстрее|увеличь\w*|прибавь\w*|добавь|длиннее|побольше|увеличить|"
                    r"сильнее|чуть больше|ещё|еще)\b")
ADJ_DOWN = re.compile(r"\b(меньше|ниже|медленнее|помедленнее|уменьши\w*|убавь\w*|короче|поменьше|уменьшить|"
                      r"слабее|чуть меньше)\b")
INFO_RE = re.compile(r"^(?:что\s+(?:такое|значит|делает|даёт|дает|означает|это\s+такое)|"
                     r"зачем\s+(?:нужн\w*|нужно|нужна|нужен)|расскажи\s+(?:мне\s+)?(?:о|об|про|по)|"
                     r"объясни\s+(?:мне\s+)?(?:что\s+(?:такое|значит|делает)\s+)?|"
                     r"информаци\w*\s+(?:о|об|про|по)|инфо\s+(?:о|об|про|по)|описание)\s*(.+)$")


def _range_text(a):
    return f"от {a.lo} до {a.hi}" + (f" {a.unit}" if a.unit and a.unit != 'мин' else "")


def _adjust_to(a, value, prev=None):
    """Выставить значение настройки. Возвращает Reply (и запоминает действие для «назад» и «ещё»)."""
    if value < a.lo or value > a.hi:
        return Reply(f"«{a.name}» принимает значения {_range_text(a)}. Назови число из этого диапазона 🔢", "curious")
    if prev is None:
        prev = a.get()
    try:
        ok, msg = a.set(value)
    except Exception as e:
        ok, msg = False, str(e)
    if not ok:
        return Reply(f"{a.name}: не получилось ({msg or 'Windows отказала'}) 😔", "sad")
    context.remember("adjust",
                     repeat=lambda: _adjust_to(a, min(a.hi, value + a.step), prev=value),
                     undo=(lambda: _adjust_to(a, prev, prev=value)) if prev is not None else None)
    note = f" {a.note}" if a.note else ""
    return Reply(f"{a.name} — {a.label(value)} ✅{note}", "happy")


def _adjust_info(a):
    cur = a.get()
    now = f"сейчас {a.label(cur)}" if cur is not None else "текущее значение Windows не читается"
    return Reply(f"{a.name}: {now}. Скажи «поставь {a.keys[0]} на N» ({_range_text(a)}) или «больше/меньше».", "curious")


def _adjust(ql, ctx):
    a = components.find_adjust(ql)
    if not a:
        return None
    mins = re.search(r"(\d+)\s*(?:час\w*|ч)\b", ql)
    nums = [int(x) for x in re.findall(r"(?<![\w.])(\d{1,4})(?![\w.])", ql)]
    if a.unit == "мин" and mins:
        value = int(mins.group(1)) * 60
    elif nums:
        value = nums[0]
    else:
        value = None
    up, down = ADJ_UP.search(ql), ADJ_DOWN.search(ql)
    if value is None and not (up or down):
        return _adjust_info(a) if (ADJ_VERB.search(ql) or re.search(r"\bсейчас|какая|какой|какое|сколько", ql)) else None
    if value is None:
        cur = a.get()
        cur = a.lo if cur is None else cur
        value = cur + a.step if (up and not down) else cur - a.step
        value = max(a.lo, min(a.hi, value))
    if not (ADJ_VERB.search(ql) or up or down or nums):
        return None
    return _adjust_to(a, value)


def _choice(ql, ctx):
    """«размер панели задач большая», «размер меню пуск меньше», «качество видео записи высокое»."""
    found = components.find_choice(ql)
    if not found:
        return None
    c, opt = found
    if opt is None:
        if not (ADJ_VERB.search(ql) or re.search(r"какой|какая|какое|сейчас|сколько|варианты", ql)):
            return None
        cur = c.get() if c.get else None
        now = f"сейчас {cur}" if cur is not None else "текущее значение не читается"
        names = ", ".join(lbl for _, lbl, _ in c.options)
        return Reply(f"{c.name}: {now}. Можно выбрать: {names}. Скажи «поставь {c.keys[0]} …» и вариант.", "curious")
    label, value = opt
    try:
        ok, msg = c.set(value)
    except Exception as e:
        ok, msg = False, str(e)
    if not ok:
        return Reply(f"{c.name}: не получилось ({msg or 'Windows отказала'}) 😔", "sad")
    note = f" {c.note}" if c.note else ""
    return Reply(f"{c.name} — {label} ✅{note}", "happy")


def _info(ql, ctx):
    """«что такое брандмауэр», «зачем нужна служба печати»: что это, что изменится, текущее состояние."""
    m = INFO_RE.search(ql.strip(" ?!.,"))
    if not m:
        return None
    topic = m.group(1).strip(" ?!.,")
    kind, obj = components.find_toggle_or_adjust(topic)
    if kind is None:
        fc = components.find_choice(topic)
        if fc is None:
            return None
        kind, obj = "choice", fc[0]
    name = obj.name
    text = settings_info.info_for(name) or "Описания пока нет."
    if kind == "choice":
        cur = obj.get() if obj.get else None
        state = f"Сейчас: {cur}." if cur is not None else ""
        names = ", ".join(lbl for _, lbl, _ in obj.options)
        how = f"Можно выбрать: {names}. Скажи «поставь {obj.keys[0]} …» и вариант."
    elif kind == "adjust":
        cur = obj.get()
        state = f"Сейчас: {obj.label(cur)}." if cur is not None else ""
        how = f"Скажи «поставь {obj.keys[0]} на N» ({_range_text(obj)}) или «больше/меньше»."
    else:
        st = None
        try:
            st = obj.get() if obj.get else None
        except Exception:
            st = None
        state = "Сейчас: включено." if st else "Сейчас: выключено." if st is False else ""
        how = (f"Открою эту страницу: скажи «открой настройки {obj.keys[0]}»." if obj.page and not obj.fn
               else f"Скажи «включи {obj.keys[0]}» или «выключи {obj.keys[0]}».")
    note = f"\n{obj.note}" if getattr(obj, "note", "") and kind == "toggle" and not obj.page else ""
    text = text.rstrip(".")
    return Reply(f"{name}. {text}. {state} {how}{note}".replace("  ", " ").replace("..", ".").strip(), "curious")


# ============================ Точка входа ============================
VERBS = (r"открой|запусти|включи|выключи|отключи|поставь|установи|сделай|закрой|переключи\w*|заблокируй|сверни|"
         r"разверни|убавь|прибавь|перейди|сделай")


def _split(ql):
    if re.match(r"\s*(напомни|найди|поищи|загугли|ищи)", ql):
        return [ql]
    parts = re.split(rf"\s*(?:,|;|\bи\b|\bа потом\b|\bпотом\b|\bзатем\b|\bпосле этого\b|\bа также\b)\s+"
                     rf"(?=(?:{VERBS})\b)", ql)
    return [p.strip() for p in parts if p.strip()]


def _one(ql, ctx):
    for fn in (_adjust, _choice, _power, _timer, lambda q, c: reminder(q, c.notify), _websearch, _links, _info, _audio_screen,
               _windows, _music, _toggles, _system, _open_close, _toggle_fallback, lambda q, c: sysinfo(q)):
        try:
            r = fn(ql, ctx)
        except Exception as e:        # одна упавшая команда не должна ронять Mico
            return Reply(f"Не получилось выполнить: {e}", "worried")
        if r:
            return r
    return None


def handle(q, notify=lambda t: None, last_hwnd=lambda: None):
    ql = normalize(q)
    r = _pending(ql)
    if r:
        return r
    ctx = Ctx(notify, last_hwnd)
    r = _followup(ql, ctx)
    if r:
        return r
    replies = [r for r in (_one(p, ctx) for p in _split(ql)) if r]
    if not replies:
        return None
    if len(replies) == 1:
        return replies[0]
    return Reply("\n".join(r.text for r in replies if r.text), replies[-1].mood)
