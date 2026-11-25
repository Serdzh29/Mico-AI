"""Управление Windows по команде: модель выбирает действие из списка, Mico AI проверяет его и выполняет.
Всё, что что-то меняет на компьютере, выполняется только после подтверждения «да».
Здесь чистая логика: разбор ответа модели, проверка аргументов и PowerShell, описание действия.
Сами действия (execute) вызывают winctl, commands и actions и работают только на Windows."""
import json, re, time

READ, OPEN, CHANGE, DANGER = "read", "open", "change", "danger"
MAX_TEXT = 1500

CATALOG = {
    "open_app": {"risk": OPEN, "args": {"name": str},
                 "about": "открыть программу по названию, например «блокнот»"},
    "open_file": {"risk": OPEN, "args": {"path": str},
                  "about": "открыть файл или папку по полному пути"},
    "open_settings": {"risk": OPEN, "args": {"page": str},
                      "about": "открыть страницу параметров Windows, например bluetooth, display, network"},
    "set_volume": {"risk": CHANGE, "args": {"percent": int}, "about": "громкость от 0 до 100"},
    "search_files": {"risk": CHANGE, "args": {"query": str},
                     "about": "найти файлы и папки по имени в твоих документах и загрузках (содержимое не читаем)"},
    "player": {"risk": OPEN, "args": {"action": str},
               "about": "плеер видео: play_pause, fullscreen, subtitles_on, subtitles_off, mute, next, prev, theater"},
    "video_open": {"risk": OPEN, "args": {"site": str, "query": str, "count": int, "fullscreen": bool},
                   "about": "включить видео на youtube, rutube, vk или ya: count — какое по счёту из выдачи, fullscreen — сразу на весь экран"},
    "video_vote": {"risk": CHANGE, "args": {"action": str},
                   "about": "поставить лайк или дизлайк видео (like или dislike)"},
    "video_subscribe": {"risk": CHANGE, "args": {},
                        "about": "подписаться на канал текущего видео"},
    "video_close": {"risk": CHANGE, "args": {},
                    "about": "закрыть текущее видео (вкладку с ним)"},
    "set_brightness": {"risk": CHANGE, "args": {"percent": int}, "about": "яркость экрана от 0 до 100"},
    "set_theme": {"risk": CHANGE, "args": {"mode": str}, "about": "тема Windows: light или dark"},
    "close_window": {"risk": CHANGE, "args": {"title": str},
                     "about": "закрыть окно, в заголовке которого есть этот текст"},
    "set_service": {"risk": DANGER, "args": {"name": str, "on": bool},
                    "about": "включить или выключить службу Windows (нужны права администратора)"},
    "run_powershell": {"risk": DANGER, "args": {"script": str},
                       "about": "выполнить команду PowerShell, если ни одно другое действие не подходит"},
    # Вкладки, окна, полный экран и музыка: ничего не удаляют и не меняют в системе, поэтому без «да»
    "open_url": {"risk": OPEN, "args": {"url": str},
                 "about": "открыть сайт или страницу в браузере, например «ютуб» или «apple.com»"},
    "new_tab": {"risk": OPEN, "args": {},
                "about": "открыть новую пустую вкладку в браузере, которым пользуешься"},
    "focus_window": {"risk": OPEN, "args": {"title": str},
                     "about": "перейти в уже открытое окно, в заголовке которого есть этот текст"},
    "window_state": {"risk": OPEN, "args": {"state": str},
                     "about": "свернуть, развернуть или восстановить последнее окно: minimize, maximize или restore"},
    "fullscreen": {"risk": OPEN, "args": {"on": bool},
                   "about": "полноэкранный режим у последнего окна (видео, презентация): true — включить, false — выйти"},
    "web_search": {"risk": OPEN, "args": {"query": str, "open_first": bool},
                   "about": "поиск в интернете: open_first false — открыть поиск Google, true — открыть первый результат"},
    "media": {"risk": OPEN, "args": {"command": str},
              "about": "музыка или видео: play_pause — пауза или продолжить, next — следующий, prev — предыдущий, stop — остановить"},
}

# Значения для новых действий: что модель может прислать и во что это превращается
WINDOW_STATES = {"minimize": 6, "maximize": 3, "restore": 9}          # коды ShowWindow Windows
WINDOW_STATE_ALIASES = {"свернуть": "minimize", "сверни": "minimize", "развернуть": "maximize",
                        "разверни": "maximize", "восстановить": "restore", "вернуть": "restore"}
MEDIA_KEYS = {"play_pause": "play", "next": "next", "prev": "prev", "stop": "stop"}   # клавиши мультимедиа Windows
MEDIA_ALIASES = {"pause": "play_pause", "play": "play_pause", "пауза": "play_pause", "продолжить": "play_pause",
                 "пауза/продолжить": "play_pause", "дальше": "next", "следующий": "next", "следующий трек": "next",
                 "назад": "prev", "предыдущий": "prev", "предыдущий трек": "prev", "остановить": "stop", "стоп": "stop"}

# Что в PowerShell не выполняем вообще. Это страховка, а не песочница: главная защита — подтверждение.
BLOCKED_PS = [
    (r"-enc(odedcommand)?\b", "закодированные команды нельзя проверить, поэтому не выполняю"),
    (r"\b(iex|invoke-expression)\b", "динамический запуск кода запрещён"),
    (r"downloadstring|downloadfile|invoke-webrequest|invoke-restmethod|start-bitstransfer|\bcurl\b|\bwget\b",
     "скачивание из интернета запрещено"),
    (r"format-volume|clear-disk|remove-partition|diskpart|bcdedit|\bformat\s+[a-z]:",
     "действия с дисками и загрузкой запрещены"),
    (r"remove-item(?=[^\n]*-recurse)(?=[^\n]*(?:c:\\windows|program files))", "массовое удаление системных папок запрещено"),
    (r"reg\s+delete\s+hklm|remove-itemproperty[^\n]*hklm", "удаление системного реестра запрещено"),
]


def risk(name):
    return CATALOG[name]["risk"]


# Сколько раз пользователь отказался от действия, после которого открытие тоже спрашиваем заранее.
# Строже, а не свободнее: это только добавляет «да», никогда не убирает.
REJECT_LIMIT = 3

# Отмена — честно по каждому действию. Где обратного действия нет, пишем почему.
UNDO_NOTE = {
    "open_app": "программа закрывается вручную, обратной команды нет",
    "open_file": "файл или папка закрываются вручную",
    "open_settings": "окно параметров закрывается вручную",
    "set_volume": "прежнее значение не запоминаю: вернуть можно командой «громкость N»",
    "set_brightness": "прежнее значение не запоминаю: вернуть можно командой «яркость N»",
    "set_theme": "обратное действие: вторая тема",
    "close_window": "окно закрыто, восстановить нельзя",
    "set_service": "обратное действие: службу выключают или включают обратно",
    "run_powershell": "команда без обратного действия: отменить нельзя",
    "open_url": "страницу закрываешь вручную, обратной команды нет",
    "new_tab": "вкладку закрываешь вручную, обратной команды нет",
    "focus_window": "переход к окну ничего не меняет, отменять нечего",
    "window_state": "прежнее состояние окна не запоминаю: вернуть можно командой «восстанови окно»",
    "fullscreen": "полный экран отменяется командой с противоположным значением",
    "media": "музыку переключили — отменить нельзя: скажи «пауза» или «предыдущий трек»",
    "web_search": "поиск открывается в браузере, отменять нечего",
    "search_files": "поиск ничего не меняет — отменять нечего",
    "player": "переключение плеера отменять нечего",
    "video_open": "просмотр ничего не меняет — отменять нечего",
    "video_vote": "лайк убирается тем же нажатием",
    "video_subscribe": "отписаться можно на странице канала",
    "video_close": "видео закрыто, открыть можно поиском снова",
}


def needs_confirm(name, rejects=0):
    """Изменения и опасные действия — только после «да». Открытие и чтение — сразу, пока
    пользователь не отказывался от него несколько раз (rejects) — тогда тоже спрашиваем."""
    return risk(name) in (CHANGE, DANGER) or rejects >= REJECT_LIMIT


def inverse(name, args):
    """Обратное действие для отмены. None — отменить нельзя или прежнее значение не запоминается."""
    if name == "set_theme":
        return "set_theme", {"mode": "light" if args.get("mode") == "dark" else "dark"}
    if name == "set_service":
        return "set_service", {"name": args.get("name"), "on": not bool(args.get("on"))}
    if name == "fullscreen":                                   # задаём состояние явно, а не переключаем: отмена точная
        return "fullscreen", {"on": not bool(args.get("on"))}
    return None


def check_script(script):
    """None — скрипт можно показать и выполнить после «да»; иначе — причина отказа."""
    if len(script) > MAX_TEXT:
        return "команда слишком длинная"
    for pattern, reason in BLOCKED_PS:
        if re.search(pattern, script, re.IGNORECASE):
            return reason
    return None


# Файлы, которые при открытии ЗАПУСКАЮТСЯ. Модель через open_file их не открывает: только вы сами.
EXEC_EXT = (".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jse", ".wsf", ".msi", ".lnk", ".scr", ".com",
            ".reg", ".hta", ".jar", ".appref-ms", ".url", ".cpl", ".msc")


def is_executable(path):
    return str(path).lower().rstrip(" .").endswith(EXEC_EXT)


BOOL_WORDS = {"true": True, "да": True, "on": True, "вкл": True, "включить": True,
              "false": False, "нет": False, "off": False, "выкл": False, "выключить": False}


def _as_bool(v):
    """true/false и «да»/«нет» — тоже ответ. Что непонятно — None."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return BOOL_WORDS.get(v.strip().lower())
    return None


def validate(obj):
    """Проверяет вызов из ответа модели и приводит аргументы к нужным типам. Возвращает (имя, аргументы)."""
    name = obj.get("action")
    if name not in CATALOG:
        raise ValueError("такого действия нет")
    args = obj.get("args") or {}
    if not isinstance(args, dict):
        raise ValueError("аргументы должны быть объектом")
    out = {}
    for key, typ in CATALOG[name]["args"].items():
        if key not in args:
            raise ValueError(f"не хватает параметра «{key}»")
        v = args[key]
        if name == "open_file" and key == "path" and is_executable(v):
            raise ValueError("программы и скрипты этим действием не запускаю — запусти их сам")
        if typ is int:
            if isinstance(v, bool):
                raise ValueError(f"«{key}» должно быть числом")
            try:
                v = max(0, min(100, int(v)))
            except (TypeError, ValueError):
                raise ValueError(f"«{key}» должно быть числом")
        elif typ is bool:
            v = _as_bool(v)
            if v is None:
                raise ValueError(f"«{key}» должно быть да или нет")
        else:
            v = str(v).strip()
            if not v or len(v) > MAX_TEXT:
                raise ValueError(f"«{key}» пустое или слишком длинное")
        out[key] = v
    if name == "set_theme" and out["mode"] not in ("light", "dark"):
        raise ValueError("тема бывает light или dark")
    if name == "window_state":
        state = WINDOW_STATE_ALIASES.get(out["state"].lower(), out["state"].lower())
        if state not in WINDOW_STATES:
            raise ValueError("окно можно свернуть, развернуть или восстановить")
        out["state"] = state
    if name == "media":
        command = MEDIA_ALIASES.get(out["command"].lower(), out["command"].lower())
        if command not in MEDIA_KEYS:
            raise ValueError("музыка бывает: play_pause, next, prev или stop")
        out["command"] = command
    if name == "open_settings" and not re.fullmatch(r"[a-z-]{2,40}", out["page"]):
        raise ValueError("страница параметров задаётся словом, например bluetooth")
    if name == "set_service" and not re.fullmatch(r"[\w.-]{1,80}", out["name"]):
        raise ValueError("некорректное имя службы")
    if name == "run_powershell":
        reason = check_script(out["script"])
        if reason:
            raise ValueError(reason)
    return name, out


def parse(text):
    """Ищет в ответе модели вызов действия. None — обычный ответ без действия.
    Принимает полный формат {"action": ..., "args": ...} и компактный
    {"set_brightness": 50}, который иногда возвращают небольшие модели."""
    if not text:
        return None
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[m.start():])
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        if "action" in obj:
            return validate(obj)
        if len(obj) == 1:
            name, value = next(iter(obj.items()))
            spec = CATALOG.get(name)
            if spec and len(spec["args"]) == 1:
                key = next(iter(spec["args"]))
                args = value if isinstance(value, dict) else {key: value}
                return validate({"action": name, "args": args})
    return None


def prompt():
    """Список действий для модели. Добавляется ТОЛЬКО к просьбам, похожим на команду для компьютера."""
    lines = ["Команда для компьютера — ответь ТОЛЬКО JSON вида {\"action\": \"имя\", \"args\": {...}}, без пояснений.",
             "Во всех остальных случаях (вопрос, разговор, объяснение) — обычный текст, никогда не JSON.",
             "Действия:"]
    for name, spec in CATALOG.items():
        args = ", ".join(f"{k}: {'число' if t is int else 'да/нет' if t is bool else 'текст'}"
                         for k, t in spec["args"].items())
        lines.append(f"- {name}({args}) — {spec['about']}")
    return "\n".join(lines)


ACTION_HINT = re.compile(
    r"загугли|погугли|гугли|поищи|найди[^?]{0,20}(интернет|гугл|google|яндекс|в сети)|на ютуб|в ютуб|"
    r"откр|закр|запуст|включ|выключ|отключ|выруб|отруб|громк|звук|яркост|ярче|темнее|тём|тем[нау]|светл|"
    r"служб|powershell|скрипт|окн|приложен|программ|настро|параметр|файл|папк|режим|команд|"
    # новые действия — только в командных фразах: «какая твоя музыка?» или «что такое сайт» не должны вызывать каталог
    r"(откр|созд|добав|перейд|зайд)\w*\s+[^?]{0,30}?(сайт|страниц|вкладк)|нов\w*\s+вкладк|полн\w*\s*экран|весь экран|"
    r"выйди из|выйти из|сверни|разверни|пауз|останов|\bстоп\b|продолжи|возобнови|(следующ|предыдущ)\w*\s+(трек|песн|видео)|"
    r"пропусти")


def wants_action(q):
    """Похоже ли сообщение на просьбу сделать что-то на компьютере. Обычные вопросы и разговор — нет."""
    ql = (q or "").lower().replace("ё", "е")
    return bool(ACTION_HINT.search(ql))


def looks_like_call(text):
    """Модель пыталась вызвать действие (JSON есть), но разобрать его не удалось. Тогда даём ей исправиться."""
    t = str(text or "")
    if '"action"' in t:
        return True
    return any(f'"{name}"' in t for name in CATALOG)


def action_schema():
    """JSON-схема вызова действия. Передаётся как грамматика llama.cpp: повтор строго валиден,
    битый JSON невозможен в принципе — только имя действия из каталога."""
    return json.dumps({
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": sorted(CATALOG)},
            "args": {"type": "object", "additionalProperties": True},
        },
        "required": ["action"],
        "additionalProperties": False,
    }, ensure_ascii=False)


def repair_prompt(raw, reason):
    """Просьба исправить вызов действия: модель получает причину отказа и свой прежний ответ."""
    return (f"Твой ответ не прошёл проверку вызова действия: {reason}.\n"
            f"Твой прежний ответ:\n{str(raw)[:600]}\n\n"
            f"Ответь заново: ТОЛЬКО корректный JSON вида {{\"action\": \"имя\", \"args\": {{...}}}} "
            f"из списка действий, либо обычным текстом, если действие не нужно.")


# Чем должна подтверждаться просьба: без этих слов в самом сообщении действие не выполняем.
GROUND = {
    "open_app": r"откр|запуст|зайд|покаж|включ",
    "open_file": r"откр|покаж|файл|папк|документ",
    "open_settings": r"настро|параметр|откр|покаж",
    "set_volume": r"громк|звук",
    "search_files": r"найди|поищи|поиск|ищем|где (у меня )?(файл|документ|папк)",
    "player": r"субтитр|видео|ролик|фильм|плеер|пауз|звук|серия|смотр|ютуб|youtube|рутуб|rutube|вк видео|яндекс видео",
    "video_open": r"видео|ролик|клип|ютуб|youtube|рутуб|rutube|вк видео|яндекс видео",
    "video_vote": r"лайк|дизлайк|нравится|оцен",
    "video_subscribe": r"подпис",
    "video_close": r"закрой|закрыть|убер",
    "set_brightness": r"яркост|ярч|темн|экран",
    "set_theme": r"тем|режим",
    "set_service": r"служб",
    "run_powershell": r"powershell|скрипт|команд",
    # Для новых действий нужен глагол действия: «что такое вкладка» или «расскажи про музыку» — не команда
    "open_url": r"откр|зайд|перейд|покаж|запуст",
    "new_tab": r"(откр|созд|добав|нов\w*)[^?]{0,20}вкладк",
    "focus_window": r"переключ|перейд|перейди|смени",
    "window_state": r"сверни|разверни|восстанов|вернуть окно",
    "media": r"пауз|останов|стоп|продолж|возобнов|(следующ|предыдущ)\w*\s+(трек|песн|композиц|видео)|трек дальше|пропусти",
    "web_search": r"загугли|погугли|гугли|поищи|найди[^?]{0,20}(интернет|гугл|google|яндекс|в сети)|(найди|включи|поставь|покажи)[^?]{0,10}видео|на ютуб|в ютуб",
}
FS_TERM = re.compile(r"полноэкран|полный экран|весь экран|на весь|во весь")
FS_VERB = re.compile(r"включ|постав|сделай|переведи|выключ|выйд|выйти|выход|отключ|убер|на весь|во весь")
FS_OFF = re.compile(r"выйд|выйти|выход|выключ|отключ|убер|не на весь|из полн")


def grounded(name, args, q):
    """Проверка, что действие — ответ на просьбу, а не случайная выдумка модели.
    Иначе модель пишет «закрыть окно» на любой вопрос: такой вызов не выполняем."""
    ql = (q or "").lower().replace("ё", "е")
    if name == "close_window":
        if not re.search(r"закр|закрой|закрыть", ql):
            return False
        words = [w for w in re.findall(r"[a-zа-я0-9]+", args.get("title", "").lower().replace("ё", "е"))
                 if len(w) >= 3]
        return bool(words) and any(w in ql for w in words)
    if name == "fullscreen":                                # направление тоже должно совпасть: «выйди» — не «включи»
        if not (FS_TERM.search(ql) and FS_VERB.search(ql)):
            return False
        return bool(args.get("on")) == (FS_OFF.search(ql) is None)
    pattern = GROUND.get(name)
    return bool(pattern and re.search(pattern, ql))


def describe(name, args):
    """Фраза для подтверждения: что именно Mico AI сделает."""
    if name == "open_app":
        return f"открыть «{args['name']}»"
    if name == "open_file":
        return f"открыть «{args['path']}»"
    if name == "open_settings":
        return f"открыть параметры Windows: {args['page']}"
    if name == "set_volume":
        return f"громкость {args['percent']}%"
    if name == "search_files":
        return f"поискать файлы по запросу «{args['query']}»"
    if name == "player":
        words = {"play_pause": "поставить на паузу или продолжить", "fullscreen": "полный экран",
                 "subtitles_on": "включить субтитры", "subtitles_off": "отключить субтитры",
                 "mute": "переключить звук", "next": "следующее видео", "prev": "предыдущее видео",
                 "theater": "режим кинотеатра"}
        return words.get(args["action"], args["action"])
    if name == "video_open":
        where = {"youtube": "на YouTube", "rutube": "на Rutube", "vk": "на VK Видео", "ya": "на Яндекс Видео"}
        return (f"включить {args.get('count') or 1}-е видео «{args.get('query') or 'без темы'}» "
                f"{where.get(args.get('site'), 'в интернете')}"
                + (" на весь экран" if args.get("fullscreen") else ""))
    if name == "video_vote":
        return "поставить лайк" if args.get("action") == "like" else "поставить дизлайк"
    if name == "video_subscribe":
        return "подписаться на канал"
    if name == "video_close":
        return "закрыть видео"
    if name == "set_brightness":
        return f"яркость {args['percent']}%"
    if name == "set_theme":
        return "тёмная тема" if args["mode"] == "dark" else "светлая тема"
    if name == "close_window":
        return f"закрыть окно «{args['title']}»"
    if name == "set_service":
        return f"{'включить' if args['on'] else 'выключить'} службу «{args['name']}»"
    if name == "run_powershell":
        return "выполнить команду PowerShell:\n" + args["script"]
    if name == "open_url":
        return f"открыть страницу «{args['url']}»"
    if name == "new_tab":
        return "открыть новую вкладку"
    if name == "focus_window":
        return f"перейти в окно «{args['title']}»"
    if name == "window_state":
        return {"minimize": "свернуть окно", "maximize": "развернуть окно",
                "restore": "восстановить окно"}[args["state"]]
    if name == "fullscreen":
        return "включить полноэкранный режим" if args["on"] else "выйти из полноэкранного режима"
    if name == "web_search":
        return f"поиск в интернете: «{' '.join(str(args['query']).split())[:80]}»"
    if name == "media":
        return {"play_pause": "пауза или продолжить музыку", "next": "следующий трек",
                "prev": "предыдущий трек", "stop": "остановить воспроизведение"}[args["command"]]
    return f"{name} {args}"


def execute(name, args, notify=lambda t: None, last_hwnd=lambda: None):
    """Выполняет действие. Возвращает текст ответа. Работает только на Windows.
    last_hwnd() — окно, с которым пользователь работал до Mico: вкладки, полный экран и окна относятся к нему."""
    from win import commands
    from win import actions
    from win import system as winctl
    if name == "search_files":                 # поиск по именам: содержимое файлов не читаем
        from win import filefind
        query = str(args.get("query") or "").strip()
        notify(f"Ищу файлы: {query}")
        return filefind.format_hits(filefind.search(filefind.user_roots(), query), query)
    if name in ("player", "video_vote", "video_subscribe", "video_close"):
        from win import videos, agentwin as agent_win
        from win import agent as agent_mod
        drv = agent_win.WinDriver(fallback=last_hwnd, notify=notify)
        snap = drv.snapshot()
        if not videos.looks_like_player(snap.get("title")):
            return "Сейчас не вижу открытого видео. Сначала открой видео и повтори команду."
        buttons = snap.get("buttons") or []
        if name == "player":
            action = str(args.get("action") or "")
            if action in ("subtitles_on", "subtitles_off"):
                want = action == "subtitles_on"
                if not videos.subtitles_press(want):
                    return f"Субтитры уже {'включены' if want else 'выключены'}."
                ok, msg = drv.do(agent_mod.PRESS, {"key": "c"})
                return f"Субтитры {'включил' if want else 'отключил'}." if ok else f"Не получилось: {msg}"
            key = videos.player_key(action)
            if not key:
                return f"Не знаю действия «{action}» для плеера."
            ok, msg = drv.do(agent_mod.PRESS, {"key": key})
            return "Готово 🎬" if ok else f"Не получилось: {msg}"
        if name == "video_vote":
            action = str(args.get("action") or "like")
            for label in videos.click_names(action):
                ok, _msg = drv.do(agent_mod.CLICK, {"name": label})
                if ok:
                    return "Лайк поставил 👍" if action == "like" else "Дизлайк поставил 👎"
            return "Не нашёл кнопку лайка на странице."
        if name == "video_subscribe":
            if videos.is_subscribed(buttons):
                return "Ты уже подписан на этот канал."
            for label in videos.click_names("subscribe"):
                ok, _msg = drv.do(agent_mod.CLICK, {"name": label})
                if ok:
                    return "Подписался на канал ✓"
            return "Не нашёл кнопку «Подписаться»."
        if name == "video_close":
            ok, msg = drv.do(agent_mod.PRESS, {"key": "ctrl+w"})
            return "Закрыл видео." if ok else f"Не получилось закрыть: {msg}"
    if name == "video_open":
        from win import videos, agentwin as agent_win
        from win import agent as agent_mod
        site = videos.service_key(args.get("site"))
        query = str(args.get("query") or "").strip()
        count = max(1, min(videos.MAX_VIDEOS, int(args.get("count") or 1)))
        notify(f"Ищу видео на {videos.SERVICES[site]['title']}…")
        winctl.open_url(videos.search_url(site, query))
        time.sleep(3)                                      # дать выдаче загрузиться
        drv = agent_win.WinDriver(fallback=last_hwnd, notify=notify)
        snap = drv.snapshot()
        pick = videos.pick_video(snap.get("buttons") or [], query, count)
        if not pick:
            return f"Не нашёл подходящего видео в выдаче {videos.SERVICES[site]['title']}. Попробуй другой запрос."
        ok, msg = drv.do(agent_mod.CLICK, {"name": pick})
        if not ok:
            return f"Нашёл «{pick[:60]}», но не смог нажать: {msg}"
        time.sleep(2)                                      # дать видео запуститься
        if args.get("fullscreen"):
            drv.do(agent_mod.PRESS, {"key": "f"})
        return f"Включаю «{pick[:60]}» на {videos.SERVICES[site]['title']} 🎬"
    if name == "open_url":
        url = commands.site_url(args["url"])
        if not url:
            return f"Не понял адрес «{args['url']}». Скажи адрес, например apple.com."
        winctl.open_url(url)
        return "Открыл страницу."
    if name == "new_tab":
        ok, msg = winctl.new_tab(last_hwnd())
        return msg
    if name == "focus_window":
        found = winctl.find_windows([args["title"]])
        if not found:
            return f"Не нашёл открытое окно «{args['title']}»."
        winctl.focus(found[0][0])
        return "Перешёл в окно."
    if name == "window_state":
        h = last_hwnd()
        if not h:
            return "Не вижу окна, которое можно поменять."
        winctl.show_window(h, WINDOW_STATES[args["state"]])
        return "Готово."
    if name == "fullscreen":
        ok, msg = winctl.set_fullscreen(last_hwnd(), args["on"])
        return msg
    if name == "media":
        winctl.press(MEDIA_KEYS[args["command"]])
        return "Готово."
    if name == "web_search":
        from web import find as webfind
        spec = {"kind": "google", "query": " ".join(str(args["query"]).split())[:200],
                "open_first": bool(args["open_first"])}
        if not spec["query"]:
            return "Скажи, что найти."
        webfind.start(spec, webfind.browser_click, notify)
        return webfind.ack(spec)
    if name == "open_app":
        r = commands.handle(f"открой {args['name']}", notify, lambda: None)
        return r.text if r else f"Не нашёл программу «{args['name']}»."
    if name == "open_file":
        import os
        if is_executable(args["path"]):
            return "Программы и скрипты этим действием не запускаю — запусти их сам."
        if not os.path.exists(args["path"]):
            return f"Не нашёл «{args['path']}»."
        os.startfile(args["path"])
        return "Открыл."
    if name == "open_settings":
        winctl.open_path(f"ms-settings:{args['page']}")
        return "Открыл параметры."
    if name == "set_volume":
        r = commands.handle(f"громкость {args['percent']}", notify, lambda: None)
        return r.text if r else "Не получилось поменять громкость."
    if name == "set_brightness":
        r = commands.handle(f"яркость {args['percent']}", notify, lambda: None)
        return r.text if r else "Не получилось поменять яркость."
    if name == "set_theme":
        r = commands.handle("включи тёмную тему" if args["mode"] == "dark" else "включи светлую тему",
                            notify, lambda: None)
        return r.text if r else "Не получилось поменять тему."
    if name == "close_window":
        hwnds = winctl.find_windows([args["title"]])
        if not hwnds:
            return f"Не нашёл окно «{args['title']}»."
        winctl.close_window(hwnds[0])
        return "Закрыл окно."
    if name == "set_service":
        ok = winctl.set_service(args["name"], args["on"])
        return "Готово." if ok else "Не получилось: нужны права администратора или службы нет."
    if name == "run_powershell":
        ok, out = winctl.ps(args["script"], timeout=120)
        return (out or ("Готово." if ok else "Команда не выполнилась."))[:1500]
    raise ValueError(f"неизвестное действие {name}")
