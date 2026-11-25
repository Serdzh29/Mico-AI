"""Режим агента (BETA): Mico сам открывает программы, нажимает кнопки и вводит текст.
Включается в настройках (вкладка «Агент»). Каждый шаг выбирает модель из короткого каталога действий.
Перед тем как что-то отправить, опубликовать, оплатить или удалить, Mico спрашивает «да». Пароли не вводит никогда.

Здесь чистая логика: разбор ответа модели, проверка шага, риск и цикл. Модель, драйвер Windows и вопрос
пользователю передаются снаружи, поэтому всё проверяется без Windows и без модели (tests/test_agent_mode.py).
Windows-часть — agent_win.py."""
import json, os, re, subprocess, threading, time

from win import messenger

MAX_STEPS = 12                 # больше шагов — задача, скорее всего, застряла
MAX_BAD_REPLIES = 3            # столько неразборчивых ответов модели подряд — остановка
CONFIRM_SEC = 60               # сколько ждём «да» перед отправкой
MAX_TYPE_LEN = 400
MAX_DONE_LEN = 500
MODEL_TOKENS = 200             # один шаг — короткий JSON; больше токенов = минуты ожидания на слабом ПК

# Клавиши и сочетания -> запись для SendKeys. Ctrl+W закрывает вкладку и может потерять данные: только после «да».
KEY_MAP = {"enter": "{ENTER}", "tab": "{TAB}", "esc": "{ESC}", "up": "{UP}", "down": "{DOWN}",
           "backspace": "{BACKSPACE}", "space": " ", "home": "{HOME}", "end": "{END}",
           "pagedown": "{PGDN}", "pageup": "{PGUP}", "f5": "{F5}",
           "ctrl+l": "^l", "ctrl+a": "^a", "ctrl+f": "^f", "ctrl+c": "^c", "ctrl+v": "^v", "ctrl+t": "^t",
           "ctrl+w": "^w", "ctrl+k": "^k", "ctrl+e": "^e",
           # клавиши плеера видео (YouTube-раскладка): k пауза, f полный экран, c субтитры, m звук
           "k": "k", "f": "f", "c": "c", "m": "m", "t": "t", "j": "j", "l": "l",
           "shift+n": "+n", "shift+p": "+p"}
KEY_ALIASES = {"return": "enter", "escape": "esc", "pgdn": "pagedown", "pgup": "pageup", "spacebar": "space"}
LAUNCH, FOCUS, CLICK, FILL, TYPE, PRESS, WAIT, DONE = ("launch", "focus", "click", "fill", "type", "press",
                                                       "wait", "done")
CATALOG = {
    LAUNCH: {"args": {"name": str}, "about": "открыть программу по названию, например «блокнот» или «телеграм»"},
    FOCUS: {"args": {"title": str}, "about": "перейти в уже открытое окно, в заголовке которого есть этот текст"},
    CLICK: {"args": {"name": str}, "about": "нажать кнопку, ссылку, вкладку, пункт меню или флажок с этим названием"},
    FILL: {"args": {"field": str, "text": str}, "about": "заполнить поле с этим названием (в том числе строку адреса и поиска в браузере) текстом"},
    TYPE: {"args": {"text": str}, "about": "напечатать текст в том поле, которое сейчас в фокусе (если поле по названию не найти)"},
    PRESS: {"args": {"key": str}, "about": "нажать клавишу или сочетание: " + ", ".join(sorted(KEY_MAP))},
    WAIT: {"args": {"sec": int}, "about": "подождать от 1 до 5 секунд, пока программа откроется"},
    DONE: {"args": {"text": str}, "about": "задача выполнена; text — короткий ответ пользователю"},
}

# Имена, которые маленькая модель иногда придумывает вместо каталога (по-английски и по-русски)
ALIASES = {
    "open": LAUNCH, "open_app": LAUNCH, "launch_app": LAUNCH, "start": LAUNCH, "start_app": LAUNCH,
    "run": LAUNCH, "app": LAUNCH, "открыть": LAUNCH, "открой": LAUNCH, "запустить": LAUNCH, "запусти": LAUNCH,
    "switch": FOCUS, "focus_window": FOCUS, "switch_window": FOCUS, "activate": FOCUS, "перейти": FOCUS,
    "button": CLICK, "press_button": CLICK, "click_button": CLICK, "tap": CLICK, "нажать": CLICK,
    "нажми": CLICK, "кликнуть": CLICK,
    "input": FILL, "input_field": FILL, "fill_field": FILL, "set_field": FILL, "field": FILL, "заполнить": FILL,
    "write": TYPE, "type_text": TYPE, "input_text": TYPE, "print": TYPE, "напечатать": TYPE,
    "ввести": TYPE, "написать": TYPE, "набрать": TYPE,
    "key": PRESS, "press_key": PRESS, "hotkey": PRESS, "keypress": PRESS, "shortcut": PRESS, "клавиша": PRESS,
    "sleep": WAIT, "delay": WAIT, "pause": WAIT, "wait_sec": WAIT, "ждать": WAIT, "подождать": WAIT,
    "finish": DONE, "complete": DONE, "finished": DONE, "answer": DONE, "готово": DONE, "выполнено": DONE,
}
# Синонимы аргументов: модель может назвать поле иначе
ARG_ALIASES = {
    "name": ("app", "program", "application", "button", "target", "item", "label", "программа", "кнопка"),
    "title": ("window", "name", "окно"),
    "field": ("name", "input", "label", "поле"),
    "text": ("value", "input", "content", "message", "string", "answer", "текст"),
    "key": ("keys", "shortcut", "hotkey", "клавиша"),
    "sec": ("seconds", "time", "duration", "секунды"),
}

# Кнопки, которыми что-то уходит наружу или необратимо меняется: только после «да»
SEND_WORDS = re.compile(r"отправ|послат|send|submit|опублик|publish|\bpost\b|оплат|\bpay\b|купит|\bbuy\b|"
                        r"заказ|\border\b|удал|delete|remove|подтверд|confirm|подпис|комментар|лайк|оцен",
                        re.IGNORECASE)
# Покупки и бронирование: перед «Оплатить» показываем цену и дату и спрашиваем дважды
BUY_WORDS = re.compile(r"оплат|купит|заказ|бронир|билет|\bцен\w*|тариф|покупк|оформи\w*\s+подписк",
                       re.IGNORECASE)
DEAL_PRICE = re.compile(r"\d[\d\s.,]{0,10}\s*(?:₽|руб|р\.|USD|\$|€|евро)", re.IGNORECASE)
DEAL_DATE = re.compile(r"\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?|(?:сегодня|завтра|послезавтра)"
                       r"|(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*\s*\d{0,2}"
                       r"|\d{1,2}:\d{2}")
# поля профиля: подставляются в сайты только после «да»; пароли не подставляются никогда
PROFILE_FIELDS = (
    (re.compile(r"им[ея]|name|first|фамил|surname|last", re.I), "user_name"),
    (re.compile(r"телефон|phone|мобил|mobile", re.I), "user_phone"),
    (re.compile(r"почт|email|e-mail|мейл", re.I), "user_email"),
)
BROWSER = re.compile(r"chrome|edge|firefox|opera|brave|яндекс|browser|браузер", re.IGNORECASE)
# Окна, где агент не работает вообще: пароли, банки, кошельки
GUARDED_WINDOWS = re.compile(r"пароль|password|keepass|bitwarden|1password|lastpass|\bбанк(?:а|у|е|ом|овск\w*)?\b|\bbank(?:ing)?\b|кошел[её]к|wallet",
                             re.IGNORECASE)

OK, CONFIRM, REFUSE = "ok", "confirm", "refuse"
HELP = ("Режим агента: напиши «агент, открой телеграм и напиши мамуле привет» или «агент, открой ютуб и включи видео». "
        "Я открою программу, найду контакт или видео, нажму нужные кнопки и введу текст. "
        "Перед отправкой, лайком, комментарием, подпиской, оплатой и удалением спрошу «да». "
        "Остановить: «стоп агент». Управляется на вкладке «Агент» в настройках.")


def zone_of(goal):
    """К какой зоне относится задача: мессенджеры, видео или программы/файлы."""
    s = (goal or "").lower().replace("ё", "е")
    if messenger.parse(goal):
        return "messenger"
    if re.search(r"видео|ролик|клип|ютуб|youtube|рутуб|rutube|вк видео|яндекс видео|плеер|фильм", s):
        return "video"
    return "apps"


def extract_deal(texts):
    """Цена и дата из подписей экрана: показать человеку перед оплатой или бронированием."""
    blob = " ".join(str(t) for t in texts if t)
    out = {}
    price = DEAL_PRICE.search(blob)
    date = DEAL_DATE.search(blob)
    if price:
        out["price"] = " ".join(price.group(0).split())
    if date:
        out["date"] = date.group(0)
    return out


def smart_fill(field, profile):
    """Значение из профиля для поля сайта. None — не подставляем: только имя, телефон и почта,
    и только если человек их заполнил. Пароли и карты не подставляются никогда."""
    for rx, key in PROFILE_FIELDS:
        if rx.search(str(field or "")):
            val = str((profile or {}).get(key) or "").strip()
            return val or None
    return None

START = re.compile(r"^агент[ ,:]+(?P<goal>.{3,300})$")
STOP = re.compile(r"^(?:стоп|останови|останов\w*|прекрати|отмени)\s+агента?$")
HELP_Q = re.compile(r"^агент\s*\??$")


# «открой блокнот и напиши привет»: открыть программу, а потом что-то в ней сделать. Одно «напиши стих» — не задача агента.
UI_TASK = re.compile(r"^(?:открой|открыть|запусти|включи|зайди в|перейди в)\s+.+?\s+(?:и|потом|затем|а затем)\s+"
                     r"(?:напиши|введи|впиши|набери|нажми|кликни|отправь|выбери|вставь|найди)\b")
# Простая задача «открой X и напиши Y»: делаем без модели — это быстрее и надёжнее на слабом ПК
PLAN = re.compile(r"^(?:открой|открыть|запусти|включи)\s+(?P<app>.+?)\s+(?:и|потом|затем|а затем)\s+"
                  r"(?:напиши|введи|впиши|набери)\s+(?P<text>.+)$", re.IGNORECASE)


def is_ui_task(q):
    """Похоже ли сообщение на задачу для агента: открыть программу и сделать что-то в ней."""
    s = " ".join((q or "").lower().replace("ё", "е").strip(" .!").split())
    return bool(UI_TASK.match(s))


def request(q):
    """Просьба агенту: ('start', задача) | ('stop', None) | ('help', None) | None — это не про агента.
    Задача сохраняет регистр: имена и тексты пишем так, как их ввёл пользователь."""
    raw = " ".join((q or "").split()).strip(" .!")
    s = raw.lower().replace("ё", "е")                       # замена «ё» не меняет длину — позиции совпадают
    if STOP.fullmatch(s):
        return "stop", None
    if HELP_Q.fullmatch(s):
        return "help", None
    m = START.match(s)
    if m:
        return "start", raw[m.start("goal"):m.end("goal")].strip()
    return None


def simple_plan(goal):
    """«открой блокнот и напиши привет» → шаги без модели. None — задача не такая простая."""
    m = PLAN.match(" ".join((goal or "").split()))
    if not m:
        return None
    app = m.group("app").strip()
    text = m.group("text").strip()[:MAX_TYPE_LEN]
    if not app or not text:
        return None
    return [(LAUNCH, {"name": app[:200]}), (WAIT, {"sec": 2}), (TYPE, {"text": text}),
            (DONE, {"text": f"Открыл «{app[:60]}» и ввёл текст."})]


def sendkeys_text(text):
    """Текст для SendKeys: спецсимволы SendKeys оборачиваем в фигурные скобки, чтобы они печатались буквально."""
    special = "+^%~(){}[]"
    return "".join("{" + c + "}" if c in special else c for c in text)


_MISSING = object()


def _pick(args, key):
    """Аргумент по его имени или по одному из частых синонимов."""
    if key in args:
        return args[key]
    for alt in ARG_ALIASES.get(key, ()):
        if alt in args:
            return args[alt]
    return _MISSING


def validate(obj):
    """Проверяет действие из ответа модели и приводит аргументы к нужным типам.
    Модель иногда называет действие по-своему («open_app», «write»), а аргументы кладёт прямо в объект
    или одной строкой — это принимаем, когда смысл однозначен."""
    raw_name = str(obj.get("action") or obj.get("tool") or "").strip().lower().replace(" ", "_").replace("-", "_")
    name = raw_name if raw_name in CATALOG else ALIASES.get(raw_name)
    if name is None:
        raise ValueError(f"нет действия «{raw_name}»")
    specs = CATALOG[name]["args"]
    args = obj.get("args")
    if args is None:                                        # аргументы лежат прямо в объекте
        args = {k: v for k, v in obj.items() if k not in ("action", "tool")}
    if not isinstance(args, dict):                          # «args»: «блокнот» — значение единственного аргумента
        if len(specs) != 1:
            raise ValueError("аргументы должны быть объектом")
        args = {next(iter(specs)): args}
    out = {}
    for key, typ in specs.items():
        v = _pick(args, key)
        if v is _MISSING:
            raise ValueError(f"не хватает «{key}»")
        if typ is int:
            if isinstance(v, bool):
                raise ValueError(f"«{key}» должно быть числом")
            try:
                m_num = re.search(r"\d+", str(v))        # «3 секунды» → 3
                v = max(1, min(5, int(m_num.group(0) if m_num else v)))
            except (TypeError, ValueError):
                raise ValueError(f"«{key}» должно быть числом")
        else:
            v = " ".join(str(v).split())
            limit = MAX_TYPE_LEN if key == "text" and name in (TYPE, FILL) else MAX_DONE_LEN if name == DONE else 200
            v = v[:limit]
            if not v:
                raise ValueError(f"«{key}» пустое")
        out[key] = v
    if name == PRESS:
        k = out["key"].lower().replace("control+", "ctrl+")
        k = KEY_ALIASES.get(k, k)
        if k not in KEY_MAP:
            raise ValueError("такой клавиши нет")
        out["key"] = k
    return name, out


def parse(raw):
    """Ответ модели → (действие, аргументы). ValueError — если в ответе нет разборчивого действия.
    Ищем все JSON-объекты в тексте: если первый испорчен, берём следующий, а не сдаёмся."""
    decoder = json.JSONDecoder()
    text = raw or ""
    error = None
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and ("action" in obj or "tool" in obj):
            try:
                return validate(obj)
            except ValueError as e:
                error = e
    if error is not None:
        raise error
    raise ValueError("в ответе нет действия")


def describe_step(name, args):
    """Что агент делает сейчас — короткой фразой, чтобы было видно ход работы."""
    if name == LAUNCH:
        return f"Агент: открываю «{args['name']}»"
    if name == FOCUS:
        return f"Агент: перехожу в окно «{args['title']}»"
    if name == CLICK:
        return f"Агент: нажимаю «{args['name']}»"
    if name == TYPE:
        return f"Агент: ввожу текст «{args['text'][:60]}»"
    if name == FILL:
        return f"Агент: заполняю «{args['field']}» текстом «{args['text'][:60]}»"
    if name == PRESS:
        return f"Агент: нажимаю клавишу {args['key']}"
    if name == WAIT:
        return f"Агент: жду {args['sec']} с"
    return "Агент: готово"


def log_to_file(text):
    """Журнал агента: %APPDATA%\\Mico\\agent.log. Ошибка записи не должна ломать работу."""
    try:
        folder = os.path.join(os.environ.get("APPDATA") or ".", "Mico")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "agent.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%d.%m %H:%M:%S ") + text + "\n")
    except Exception:
        pass


def check(name, args, snap):
    """(OK | CONFIRM | REFUSE, причина). Подтверждение нужно перед отправкой и нажатием Enter."""
    snap = snap or {}
    title = str(snap.get("title", ""))
    if GUARDED_WINDOWS.search(title) and name in (TYPE, FILL, CLICK, PRESS):
        return REFUSE, f"в окне «{title[:40]}» с паролями и деньгами агент не работает"
    if name in (TYPE, FILL) and snap.get("password"):
        return REFUSE, "фокус в поле пароля — вводить пароль не буду"
    if name == FILL and re.search(r"парол|password|\bcard\b|номер\w*\s+карт|\bcvv\b|\bcvc\b|карт\w*\s+номер|банковск\w*\s+карт", args["field"], re.I):
        return REFUSE, f"поле «{args['field']}» похоже на пароль или номер карты — не заполняю"
    if name == CLICK and SEND_WORDS.search(args["name"]):
        return CONFIRM, f"нажму «{args['name']}» в окне «{title[:40]}»"
    if name == PRESS and args["key"] == "enter":
        return CONFIRM, f"нажму Enter в окне «{title[:40]}» — он может что-то отправить"
    if name == PRESS and args["key"] == "ctrl+w":
        return CONFIRM, f"закрою вкладку или окно «{title[:40]}» (сочетание Ctrl+W)"
    return OK, ""


def model_schema():
    """JSON-схема шага агента для локальной модели: ответ всегда валидный JSON с действием из каталога."""
    return json.dumps({
        "type": "object",
        "properties": {"action": {"type": "string", "enum": sorted(CATALOG)},
                       "args": {"type": "object", "additionalProperties": True}},
        "required": ["action"], "additionalProperties": False}, ensure_ascii=False)


def prompt(goal, history, snap):
    """Просьба к модели: задача, каталог действий, что видно в активном окне и что уже сделано."""
    snap = snap or {}
    lines = [f"Ты управляешь программами на компьютере пользователя. Задача: {goal}",
             "Ответь ТОЛЬКО одним JSON вида {\"action\": \"имя\", \"args\": {...}}, без пояснений.",
             "Действия:"]
    for name, spec in CATALOG.items():
        args = ", ".join(f"{k}: {'число' if t is int else 'текст'}" for k, t in spec["args"].items())
        lines.append(f"- {name}({args}) — {spec['about']}")
    buttons = ", ".join(list(snap.get("buttons") or [])[:25]) or "нет"
    fields = ", ".join(list(snap.get("fields") or [])[:10]) or "нет"
    title = str(snap.get("title", ""))
    lines.append(f"Активное окно: «{title[:80]}». Кнопки: {buttons}. Поля: {fields}.")
    if BROWSER.search(title):
        lines.append("Это браузер. Чтобы открыть сайт, сначала ctrl+l, затем fill в строку адреса или type, потом enter. "
                     "Ссылки и кнопки сайта — в списке выше.")
    lines.append("Если нужных кнопок и полей в окне не видно (например, это игра или программа без доступности), "
                 "не угадывай: выбери done и честно скажи, что элементов не нашёл.")
    if history:
        lines.append("Уже сделано:")
        lines += ["- " + h for h in history[-8:]]
    lines.append("Когда задача выполнена, выбери done. Если не понимаешь, как продолжить, выбери done и объясни.")
    return "\n".join(lines)


class Runner:
    """Выполняет задачу в фоновом потоке.

    model(текст) -> ответ модели.
    driver: snapshot() -> dict(title, buttons, fields, password); do(name, args) -> (ok, сообщение).
    ask(вопрос) -> bool: блокирует поток до «да» (True) или «нет» (False).
    notify(текст): показать пользователю. journal(текст): записать в журнал действий (необязательно)."""

    def __init__(self, goal, model, driver, ask, notify, journal=None, max_steps=MAX_STEPS, log=None,
                 profile=None, shot=None, finished=None):
        self.goal, self.model, self.driver = goal, model, driver
        self.ask, self.notify, self.journal = ask, notify, journal or (lambda text: None)
        self.log = log or (lambda text: None)
        self.max_steps = max_steps
        self.profile = profile or {}        # имя/телефон/почта для умных полей (только после «да»)
        self.shot = shot                    # снимок экрана после шага — для отчёта (не обязательно)
        self.finished = finished            # карточка после задачи: (итог, отчёт по шагам)
        self.done_log = []                  # [(шаг, аргументы, результат)] — что уже сделано
        self._stop = threading.Event()
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._run_safe, daemon=True).start()

    def stop(self):
        self._stop.set()

    def stopping(self):
        return self._stop.is_set()

    def _run_safe(self):
        try:
            result = self.run()
        except Exception as e:                          # ошибка Windows не должна ронять Mico
            result = f"Агент остановился из-за ошибки: {e}"
        finally:
            self.running = False
        if self.finished is not None:
            self.finished(result, self.report())        # карточка «что сделал» + кнопка отмены
        else:
            self.notify(result)

    def _do(self, name, args):
        """Шаг с одним повтором: страница могла не догрузиться, кнопка появляется позже."""
        ok, msg = self.driver.do(name, args)
        if not ok and name in (CLICK, FILL):
            self.log(f"повтор шага {name} {args}: {msg}")
            self.driver.do(WAIT, {"sec": 2})
            ok, msg = self.driver.do(name, args)
        return ok, msg

    def _confirm_step(self, name, args, why):
        """Подтверждение шага. Покупки и бронирование — двойное: с ценой и датой перед «Оплатить»."""
        hay = " ".join([why] + [str(v) for v in (args or {}).values()])
        if BUY_WORDS.search(hay):
            deal = extract_deal([why] + list((args or {}).values()))
            info = ", ".join(f"{k}: {v}" for k, v in deal.items())
            if not self.ask(f"Это покупка или бронирование. Сейчас {why}. {info or 'цену и дату на экране не вижу'}. Продолжить?"):
                return False
            return self.ask(f"Последняя проверка: {why} ({info or 'цена/дата не видна'}). Точно продолжить?")
        return self.ask(f"Сейчас {why}. Продолжить?")

    def _record(self, name, args, msg=""):
        self.done_log.append((name, dict(args) if isinstance(args, dict) else args, msg or ""))
        if self.shot is not None:
            try:
                self.shot(len(self.done_log))
            except Exception:
                pass                            # снимок — удобство, не обязанность

    def report(self):
        """Что я сделал по шагам — короткая карточка после задачи."""
        if not self.done_log:
            return ""
        lines = ["Что я сделал:"]
        for i, (name, args, msg) in enumerate(self.done_log, 1):
            step = f"{i}. {describe_step(name, args)}"
            lines.append(step if not msg else step + f" — {msg}")
        return "\n".join(lines)

    def undo_plan(self):
        """Шаги, чтобы отменить последнее действие, и честная причина, если отменить нельзя."""
        if not self.done_log:
            return None, "Я ещё ничего не делал — отменять нечего."
        name, args, _msg = self.done_log[-1]
        label = str(args.get("name", "")) if isinstance(args, dict) else ""
        if name == CLICK and re.search(r"нравится|like|dislike|дизлайк", label, re.I):
            return [(CLICK, dict(args))], f"Повторно нажму «{label}» — это снимет лайк или дизлайк."
        return None, "Последний шаг отменить нельзя: так устроена программа (отправленное уже не вернуть)."

    def _focus_app(self, app):
        """Попытаться вывести окно программы на передний план (по названию)."""
        try:
            from win import system as winctl
            from win import agentwin
            found = winctl.find_windows(agentwin.window_tokens(app))   # «телеграм» → telegram, а не только русское название
            if found:
                winctl.focus(found[0][0])
                time.sleep(0.4)
                return True
        except Exception:
            pass
        return False

    def _messenger(self, task):
        """Написать контакту: открыть программу, найти чат по полному имени, проверить подпись, спросить «да», отправить."""
        app, who, text = task["app"], task["who"], task["text"]
        cands = task.get("candidates") or messenger.candidates(who)
        self.log(f"мессенджер: {app}, контакт «{who}», текст «{text[:40]}»")

        ok, msg = self._do(LAUNCH, {"name": app})
        self._record(LAUNCH, {"name": app}, "" if ok else (msg or "не вышло"))
        if not ok:
            for path in messenger.launch_paths(app):       # установки «для себя» — их нет в PATH
                try:
                    subprocess.Popen([path])
                    ok = True
                    break
                except Exception as e:
                    msg = str(e)
            if not ok:
                return f"Не открыл «{app}»: {msg or 'программа не найдена'}."
        self.journal("открыл " + app)
        if self._stop.is_set():
            return "Остановил агента по твоей просьбе."
        self._do(WAIT, {"sec": 3})
        self._focus_app(app)

        # ищем чат по полному имени в именительном падеже: «алексею» → «алексей», «мамуле» → «мамуля»
        contact, snap, blind = None, {}, False
        hotkey = messenger.search_hotkey(app)
        self._do(PRESS, {"key": hotkey})
        self._do(WAIT, {"sec": 1})
        before = set(self.driver.snapshot().get("buttons") or [])      # что окно показывает до ввода имени

        for term in cands:
            if self._stop.is_set():
                return "Остановил агента по твоей просьбе."
            self.notify(f"Ищу чат «{term}»…")
            snap = self.driver.snapshot()
            field = messenger.find_search_field(snap.get("fields") or [])
            if field:                                             # поле поиска найдено — заполняем целиком (старый текст заменяется)
                ok_fill, _ = self._do(FILL, {"field": field, "text": term})
                self._record(FILL, {"field": field, "text": term}, "" if ok_fill else "не вышло")
            else:                                                 # фокус в поиске после hotkey — стираем прошлое имя и печатаем новое
                self._do(PRESS, {"key": "ctrl+a"})
                self._do(PRESS, {"key": "backspace"})
                ok_type, _ = self._do(TYPE, {"text": term})
                self._record(TYPE, {"text": term}, "" if ok_type else "не вышло")

            # результаты поиска появляются не сразу — пробуем несколько раз
            appeared = False
            for _ in range(4):
                if self._stop.is_set():
                    return "Остановил агента по твоей просьбе."
                self._do(WAIT, {"sec": 1})
                snap = self.driver.snapshot()
                buttons = snap.get("buttons") or []
                appeared = appeared or bool(set(buttons) - before)
                contact = messenger.match_contact(cands, buttons)
                if contact:
                    break
            if contact:
                self.log(f"нашёл контакт «{contact}» по запросу «{term}»")
                break
            if not appeared:
                # Окно не показывает результаты через UI Automation (так у Telegram, MAX): чат на экране есть, но агент
                # его не «видит». Раньше он тут же начинал печатать другие варианты имени поверх первого. Теперь не гадаем:
                # открываем верхний результат поиска клавишами и просим тебя проверить, тот ли это чат.
                blind = True
                self.log(f"результаты поиска «{term}» не видны через UI Automation — открываю верхний результат клавишами")
                break

        if blind:
            term = cands[0]
            self.notify(f"Открываю верхний результат поиска «{term}»…")
            for key in messenger.pick_keys(app):
                ok_key, _ = self._do(PRESS, {"key": key})
                self._record(PRESS, {"key": key}, "" if ok_key else "не вышло")
                self._do(WAIT, {"sec": 1})
            self._do(WAIT, {"sec": 2})                                       # дать чату открыться
            contact = term
        elif not contact:
            return (f"В «{app}» не нашёл контакт «{who}» — пробовал имена: {', '.join(cands[:4])}. "
                    "Проверь, как он подписан в программе, и напиши имя так же, например «напиши Алексею привет».")
        else:
            verdict, why = check(CLICK, {"name": contact}, snap)
            if verdict == REFUSE:
                return f"Остановился: {why}."
            self.notify(f"Открываю чат «{contact}»…")
            ok, msg = self._do(CLICK, {"name": contact})
            self._record(CLICK, {"name": contact}, "" if ok else (msg or "не вышло"))
            if not ok:                 # окно не даёт нажать кнопкой — Enter открывает верхний результат поиска
                self._do(WAIT, {"sec": 1})
                ok, msg = self._do(PRESS, {"key": "enter"})
                self._record(PRESS, {"key": "enter"}, "" if ok else "не вышло")
            if not ok:
                return f"Нашёл «{contact}», но не смог открыть чат: {msg or 'нажатие не вышло'}. Открой его сам и повтори."

        self._do(WAIT, {"sec": 2})                                               # дать чату открыться
        if blind:
            question = (f"Я ввёл «{contact}» в поиск «{app}» и открыл верхний результат. Проверь на экране, что открылся "
                        f"чат «{who}». Отправить туда «{text}»?")
        else:
            question = f"Отправлю «{text}» контакту «{contact}» в «{app}». Отправить?"
        if not self.ask(question):
            return "Хорошо, не отправляю."
        if self._stop.is_set():
            return "Остановил агента по твоей просьбе."

        snap = self.driver.snapshot()
        field = messenger.find_message_field(snap.get("fields") or [])
        if field:                                              # поле ввода названо — пишем в него
            ok, msg = self._do(FILL, {"field": field, "text": text})
            self._record(FILL, {"field": field, "text": text}, "" if ok else (msg or "не вышло"))
        else:                                                  # названия нет — текст уходит в фокус
            ok, msg = self._do(TYPE, {"text": text})
            self._record(TYPE, {"text": text}, "" if ok else (msg or "не вышло"))
        if not ok:
            return f"Открыл чат «{contact}», но не смог ввести текст."

        time.sleep(1)                         # даём программе обработать текст (не шаг — не засоряем журнал)
        ok, msg = self._do(PRESS, {"key": "enter"})
        self._record(PRESS, {"key": "enter"}, "" if ok else (msg or "не вышло"))
        if not ok:
            return f"Ввёл текст в чат «{contact}», но не смог нажать Enter. Отправь сам."

        self.journal(f"агент: сообщение контакту «{contact}» в {app}")
        return f"Отправил «{text}» — {contact} ✉️"

    def run(self):
        """Цикл шагов. Возвращает итоговый текст для пользователя."""
        task = messenger.parse(self.goal)                   # «открой телеграм и напиши алексею привет»
        if task:
            return self._messenger(task)
        history, bad = [], 0
        plan = simple_plan(self.goal) or []                 # простая задача идёт по плану, без модели
        self.log(f"задача: {self.goal}" + (" (простой план, без модели)" if plan else ""))
        for _ in range(self.max_steps):
            if self._stop.is_set():
                return "Остановил агента по твоей просьбе."
            snap = self.driver.snapshot()
            self.log(f"окно: «{snap.get('title', '')}», кнопки: {len(snap.get('buttons') or [])}")
            from_plan = bool(plan)
            if from_plan:
                name, args = plan.pop(0)
            else:
                self.notify("Агент думает над следующим шагом…")
                raw = self.model(prompt(self.goal, history, snap))
                self.log(f"ответ модели: {' '.join(str(raw).split())[:300]}")
                try:
                    name, args = parse(raw)
                except ValueError as e:
                    bad += 1
                    history.append(f"ответ не разобрал: {e}")
                    self.log(f"не разобрал ответ: {e}")
                    if bad >= MAX_BAD_REPLIES:
                        return "Не смог понять, что делать дальше, и остановился. Попробуй задачу проще."
                    continue
                bad = 0
            if name == DONE:
                return args["text"]
            if name == FILL and not str(args.get("text") or "").strip(" .-\u2013\u2014\u2026"):
                # умные поля: пустое или «-» в поле заполняем из профиля, но только после «да»
                val = smart_fill(args.get("field"), self.profile)
                if val and self.ask(f"Подставить «{val}» в поле «{args['field']}»?"):
                    args = dict(args, text=val)
                else:
                    history.append(f"{name}: поле оставил пустым")
                    continue
            verdict, why = check(name, args, snap)
            if verdict == REFUSE:
                if from_plan:
                    return f"Остановился: {why}."
                history.append(f"{name}: отказался — {why}")
                continue
            if verdict == CONFIRM and not self._confirm_step(name, args, why):
                return "Хорошо, не делаю. Остановился."
            if self._stop.is_set():
                return "Остановил агента по твоей просьбе."
            self.notify(describe_step(name, args))
            ok, msg = self._do(name, args)
            self.log(f"шаг {name} {args}: {'ок' if ok else 'не вышло'} {msg}")
            self._record(name, args, "" if ok else (msg or "не вышло"))
            if from_plan and not ok:
                # самокоррекция: план споткнулся — модель дорабатывает остаток с учётом ошибки,
                # а не бросает задачу на первом же промахе
                history.append(f"план: шаг {name} не вышло ({msg or 'нет ответа'}) — придумай другой путь")
                plan = []
                bad += 1
                self.log(f"план сломался на шаге {name}, передаю модели: {msg}")
                if bad >= MAX_BAD_REPLIES:
                    return f"Не получилось: {msg or 'шаг ' + name}. Остановился."
                continue
            history.append(f"{name} {json.dumps(args, ensure_ascii=False)} → {'ок' if ok else 'не вышло'}"
                           + (f" ({msg})" if msg else ""))
            if verdict == CONFIRM and ok:
                self.journal(f"агент: {why}")
        return f"Не уложился в {self.max_steps} шагов и остановился. Посмотри, что успел."
