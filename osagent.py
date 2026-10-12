"""Управление Windows по команде: модель выбирает действие из списка, Mico проверяет его и выполняет.
Всё, что что-то меняет на компьютере, выполняется только после подтверждения «да».
Здесь чистая логика: разбор ответа модели, проверка аргументов и PowerShell, описание действия.
Сами действия (execute) вызывают winctl, commands и actions и работают только на Windows."""
import json, re

READ, OPEN, CHANGE, DANGER = "read", "open", "change", "danger"
MAX_TEXT = 1500

CATALOG = {
    "open_app": {"risk": OPEN, "args": {"name": str},
                 "about": "открыть программу по названию, например «блокнот»"},
    "open_file": {"risk": OPEN, "args": {"path": str},
                  "about": "открыть файл или папку по полному пути"},
    "find_file": {"risk": READ, "args": {"query": str},
                  "about": "найти файлы и программы на компьютере по названию"},
    "open_settings": {"risk": OPEN, "args": {"page": str},
                      "about": "открыть страницу параметров Windows, например bluetooth, display, network"},
    "set_volume": {"risk": CHANGE, "args": {"percent": int}, "about": "громкость от 0 до 100"},
    "set_brightness": {"risk": CHANGE, "args": {"percent": int}, "about": "яркость экрана от 0 до 100"},
    "set_theme": {"risk": CHANGE, "args": {"mode": str}, "about": "тема Windows: light или dark"},
    "close_window": {"risk": CHANGE, "args": {"title": str},
                     "about": "закрыть окно, в заголовке которого есть этот текст"},
    "set_service": {"risk": DANGER, "args": {"name": str, "on": bool},
                    "about": "включить или выключить службу Windows (нужны права администратора)"},
    "run_powershell": {"risk": DANGER, "args": {"script": str},
                       "about": "выполнить команду PowerShell, если ни одно другое действие не подходит"},
}

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


def needs_confirm(name):
    """Изменения и опасные действия — только после «да». Открытие и чтение — сразу."""
    return risk(name) in (CHANGE, DANGER)


def check_script(script):
    """None — скрипт можно показать и выполнить после «да»; иначе — причина отказа."""
    if len(script) > MAX_TEXT:
        return "команда слишком длинная"
    for pattern, reason in BLOCKED_PS:
        if re.search(pattern, script, re.IGNORECASE):
            return reason
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
        if typ is int:
            if isinstance(v, bool):
                raise ValueError(f"«{key}» должно быть числом")
            try:
                v = max(0, min(100, int(v)))
            except (TypeError, ValueError):
                raise ValueError(f"«{key}» должно быть числом")
        elif typ is bool:
            if not isinstance(v, bool):
                raise ValueError(f"«{key}» должно быть да или нет")
        else:
            v = str(v).strip()
            if not v or len(v) > MAX_TEXT:
                raise ValueError(f"«{key}» пустое или слишком длинное")
        out[key] = v
    if name == "set_theme" and out["mode"] not in ("light", "dark"):
        raise ValueError("тема бывает light или dark")
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
    Если JSON похож на действие, но неверен, поднимает ValueError с понятной причиной."""
    if not text or '"action"' not in text:
        return None
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and "action" in obj:
            return validate(obj)
    return None


def prompt():
    """Что модель должна знать о действиях. Добавляется к системной подсказке."""
    lines = ["Если пользователь просит что-то сделать на компьютере, ответь ТОЛЬКО одним JSON-объектом "
             "без метки настроения и без пояснений, вида {\"action\": \"имя\", \"args\": {...}}.",
             "Доступные действия:"]
    for name, spec in CATALOG.items():
        args = ", ".join(f"{k}: {'число' if t is int else 'да/нет' if t is bool else 'текст'}"
                         for k, t in spec["args"].items())
        lines.append(f"- {name}({args}) — {spec['about']}")
    lines.append("Если действие не нужно (обычный вопрос или разговор), отвечай обычным текстом.")
    return "\n".join(lines)


def describe(name, args):
    """Фраза для подтверждения: что именно Mico сделает."""
    if name == "open_app":
        return f"открыть «{args['name']}»"
    if name == "open_file":
        return f"открыть «{args['path']}»"
    if name == "find_file":
        return f"поискать «{args['query']}»"
    if name == "open_settings":
        return f"открыть параметры Windows: {args['page']}"
    if name == "set_volume":
        return f"громкость {args['percent']}%"
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
    return f"{name} {args}"


def execute(name, args, notify=lambda t: None):
    """Выполняет действие. Возвращает текст ответа. Работает только на Windows."""
    import commands, actions, winctl
    if name == "open_app":
        r = commands.handle(f"открой {args['name']}", notify, lambda: None)
        return r.text if r else f"Не нашёл программу «{args['name']}»."
    if name == "open_file":
        import os
        if not os.path.exists(args["path"]):
            return f"Не нашёл «{args['path']}»."
        os.startfile(args["path"])
        return "Открыл."
    if name == "find_file":
        return actions.find_files(args["query"].lower()).text
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
