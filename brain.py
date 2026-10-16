"""Мозг Mico: локальные модели через Ollama (только 127.0.0.1) + маршрутизация запросов."""
import base64, io, json, os, re, threading, time, webbrowser
import mss, requests, win32gui
from PIL import Image
import actions, capabilities, cleanup, clipbuf, commands, components, custom, daysum, dialog, diagnose, features, health, identity, knowledge, notes, osagent, phrase, smart, planner, pomodoro, schedule, sorter, todo, typo, updatecheck, version, windows_info, workspace, recall, intent, chatdigest
import winctl as W
from actions import Reply
from emotions import detect_emotion, split_mood

BASE = "http://127.0.0.1:11434"
KEEP_ALIVE = "30m"                        # сколько модель держится в памяти после последнего вопроса
SYSTEM = ("Ты — Mico, милый дружелюбный ИИ-компаньон на рабочем столе. Отвечай кратко и тепло, "
          "по-русски, если не просят иначе. Все данные остаются на этом ПК.")
MOOD_RULE = (" Начни ответ с одной метки настроения в квадратных скобках. Выбери ту, что ближе всего к тому, "
             "что ты чувствуешь прямо сейчас: [happy] радость и дружелюбие; [love] тепло и нежность; [sad] грусть или "
             "сочувствие; [surprised] удивление; [laugh] смех; [curious] любопытство, интерес; [worried] тревога, "
             "беспокойство за человека; [scared] испуг; [angry] злость или раздражение; [shy] смущение; "
             "[confused] растерянность, непонимание; [excited] восторг, азарт; [proud] гордость за человека или "
             "его успех; [playful] озорство, шутка, подмигивание; [thinking] размышляю; [sleepy] усталость; "
             "[idle] спокойно и ровно. Сразу после метки — сам ответ. Метку нельзя пропускать.")
FILEWORDS = (r"файл|папк|документ|фото|картинк|изображен|видео|pdf|word|excel|презентац|таблиц|скачан|"
             r"на компьютере|на пк|на диске")
GLANCE_PROMPT = ("Ты Mico — дружелюбный компаньон на экране. Посмотри на снимок экрана. Если видишь что-то, "
                 "что стоит коротко и тепло прокомментировать (интересная страница, видео, ошибка, забавная деталь), "
                 "напиши ОДНУ короткую фразу по-русски, без вступления. Если ничего особенного — ответь ровно: НИЧЕГО")
SUGGEST_TEXT = ["qwen2.5:3b", "qwen2.5:7b", "qwen2.5:14b", "llama3.2:3b", "llama3.1:8b", "gemma2:9b", "phi4"]
SUGGEST_VISION = ["moondream", "llava:7b", "qwen2.5vl:3b", "qwen2.5vl:7b", "minicpm-v", "llama3.2-vision:11b"]


def list_models():
    try:
        return sorted(m["name"] for m in requests.get(BASE + "/api/tags", timeout=2).json().get("models", []))
    except Exception:
        return []


def pull_model(name, cb):
    """Скачивание модели через локальный Ollama; cb(строка статуса). Возвращает True/False."""
    try:
        with requests.post(BASE + "/api/pull", json={"model": name, "name": name, "stream": True},
                           stream=True, timeout=None) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                d = json.loads(line)
                if d.get("error"):
                    cb("Ошибка: " + d["error"])
                    return False
                st = d.get("status", "")
                if d.get("total"):
                    st += f" {d.get('completed', 0) * 100 // d['total']}%"
                cb(st)
        return True
    except Exception as e:
        cb(f"Ошибка: {e}. Запущена ли Ollama?")
        return False


class Brain:
    def __init__(self, cfg, store, tracker):
        self.cfg, self.store, self.tracker = cfg, store, tracker
        self.dialog = dialog.Dialog(window=self.cfg.get("dialog_memory_min", 15) * 60,   # память диалога
                                    persist=self._persist_turn)                          # и журнал на диске
        self.notify = lambda text: None
        self.last_hwnd = lambda: self.tracker.last_hwnd      # main.py заменит на окно из WindowWatcher
        extra = {w for t in components.TOGGLES for k in t.keys for w in k.split() if len(w) >= 4}
        self.typo = typo.Corrector(store, extra)               # опечатки и свой словарь
        self.on_command = lambda q: None                       # main.py: учёт кнопок и команд
        self._kb = None                                        # база знаний Mico (статьи из knowledge/)
        self.save_cfg = lambda: None                           # main.py: сохранить настройки
        self.pomo = pomodoro.Pomodoro(lambda t: self.notify(t), self._pomo_cycle)
        self._handled = False

    def _chat(self, user, model, image_b64=None, use_history=False, mood_tag=False, tools=False):
        msg = {"role": "user", "content": user}
        if image_b64:
            msg["images"] = [image_b64]
        system = SYSTEM + (MOOD_RULE if mood_tag else "") + ("\n" + osagent.prompt() if tools else "")
        messages = ([{"role": "system", "content": system}] +
                    (self.dialog.messages(limit=8) if use_history else []) + [msg])
        r = requests.post(BASE + "/api/chat", json={"model": model, "messages": messages, "stream": False,
                                                    "keep_alive": KEEP_ALIVE},     # модель не выгружается между вопросами
                          timeout=300)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

    @staticmethod
    def is_screenshot(q):
        return bool(re.search(r"скриншот|скрин\b|снимок экрана|сфотографируй экран|screenshot", q.lower()))

    def _screenshot_b64(self):
        hwnd = self.tracker.last_hwnd
        with mss.mss() as sct:
            box = sct.monitors[1]
            if hwnd and win32gui.IsWindow(hwnd) and not win32gui.IsIconic(hwnd):
                l, t, r, b = win32gui.GetWindowRect(hwnd)
                if r - l > 50 and b - t > 50:
                    box = {"left": l, "top": t, "width": r - l, "height": b - t}
            shot = sct.grab(box)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img.thumbnail((1024, 1024))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return base64.b64encode(buf.getvalue()).decode()

    @staticmethod
    def _tagged(raw, default):
        """Ответ модели с меткой настроения → (текст, эмоция). Без метки — эмоция по словам, иначе default."""
        mood, text = split_mood((raw or "").strip())
        text = text.strip()
        return text, mood or detect_emotion(text) or default

    def _screen(self, prompt):
        if self.tracker.last_blocked:
            return Reply("Это окно в списке исключений (пароли/приватный режим), я его не смотрю 🙈", "worried")
        text, mood = self._tagged(self._chat(prompt, self.cfg["vision_model"], self._screenshot_b64(),
                                             mood_tag=True), "curious")
        return Reply(text, mood)

    def glance(self, recent=None):
        """Инициатива: Mico смотрит на экран и, если есть что прокомментировать, — одна короткая фраза.
        Картинка уходит только в локальную модель. Возвращает (текст, эмоция) или None."""
        if self.tracker.last_blocked:
            return None
        prompt = GLANCE_PROMPT + ("\nНе повторяй уже сказанное: " + "; ".join(recent[-3:]) if recent else "")
        raw = self._chat(prompt, self.cfg["vision_model"], self._screenshot_b64(), mood_tag=True).strip()
        txt, mood = self._tagged(raw, "curious")
        if not txt or txt.upper().startswith("НИЧЕГО") or len(txt) > 260:
            return None
        return txt.splitlines()[0].strip(), mood

    def _timeline(self, q):
        ql, now = q.lower(), time.time()
        m = re.search(r"(\d+)\s*(мин|час|ч\b)", ql)
        if m:
            secs = int(m.group(1)) * (60 if m.group(2).startswith("мин") else 3600)
        else:
            secs = 1800 if "полчаса" in ql else 3600
        t0, t1 = (now - secs - 900, now - secs + 900) if "назад" in ql else (now - secs, now)
        lines = [f"{time.strftime('%H:%M', time.localtime(s))}–{time.strftime('%H:%M', time.localtime(e))} "
                 f"{p}: {t}" for s, e, p, t in self.store.between(t0, t1) if e - s >= 5][:60]
        if not lines:
            return Reply("За это время у меня нет записей 🤔", "curious")
        raw = "\n".join(lines)
        try:
            text, mood = self._tagged(self._chat("Вот журнал активности пользователя. Кратко перескажи, чем он "
                                                 "занимался, по-человечески, 3–5 предложений:\n" + raw,
                                                 self.cfg["text_model"], mood_tag=True), "happy")
            return Reply(text, mood)
        except requests.RequestException:
            return Reply("Модель недоступна, вот сырой журнал:\n" + raw, "worried")

    def _clipboard(self, ql):
        text = actions.get_clipboard().strip()
        if not text:
            return Reply("Буфер обмена пуст 📋", "curious")
        if "исправ" in ql:
            task = "Исправь ошибки в тексте. Только исправленный текст."
        elif re.search(r"кратко|суть", ql):
            task = "Перескажи кратко."
        else:
            task = "Объясни, что это, и кратко ответь по существу."
        out, mood = self._tagged(self._chat(task + "\n\n" + text[:6000], self.cfg["text_model"], mood_tag=True), "happy")
        return Reply(out, mood)

    def warm_up(self):
        """Загружает текстовую модель в память заранее, чтобы первый ответ не ждал загрузки. Ошибки не важны:
        если модели нет, Mico всё равно работает по правилам."""
        try:
            requests.post(BASE + "/api/generate", json={"model": self.cfg["text_model"], "prompt": "",
                                                        "keep_alive": KEEP_ALIVE}, timeout=180)
        except Exception:
            pass

    def _persist_turn(self, ts, role, text):
        """Журнал разговора на диске (зашифрован). Выключается вместе с памятью в настройках."""
        if not self.cfg.get("memory_on", True):
            return
        self.store.add_chat(ts, role, text)

    def _recall(self, q):
        """«о чём мы говорили вчера» — отвечаем пересказом дня или репликами, без обращения к модели."""
        spec = recall.parse(q)
        if not spec:
            return None
        if not self.cfg.get("memory_on", True):
            return Reply("Память разговора выключена в настройках, поэтому вспомнить не могу.", "curious")
        try:
            rows = self.store.chats_between(spec["t0"], spec["t1"])
            summaries = self.store.day_summaries(chatdigest.key_of(spec["t0"]), chatdigest.key_of(spec["t1"]))
        except Exception as e:
            return Reply(f"Не получилось открыть журнал разговора: {e}", "worried")
        return Reply(recall.answer_days(rows, spec, summaries), "curious")

    # ---------- пересказ дней (в фоне, раз в час; модель вызывается только для прошедших дней) ----------
    def start_digests(self):
        threading.Thread(target=self._digest_loop, daemon=True).start()

    def _digest_loop(self):
        time.sleep(90)                                   # даём Mico открыться и модели прогреться
        while True:
            try:
                self.digest_past_days()
            except Exception:
                pass                                     # пересказ — удобство, а не обязанность
            time.sleep(3600)

    def digest_past_days(self):
        """Пишет пересказ для каждого прошедшего дня, где он ещё не готов. Возвращает, сколько написал."""
        if not self.cfg.get("memory_on", True):
            return 0
        done = 0
        for key in chatdigest.missing(time.time(), lambda t0, t1: self.store.count_chat(t0, t1) >= chatdigest.MIN_ROWS,
                                      self.store.has_day_summary):
            t0, t1 = chatdigest.bounds(key)
            text = chatdigest.prompt(self.store.chats_between(t0, t1))
            if not text:
                continue
            out = chatdigest.clean(self._chat(text, self.cfg["text_model"]))
            if out:
                self.store.add_day_summary(key, out, time.time())
                done += 1
        return done

    def ask(self, q):
        """Понимает опечатки: «открй» → «открой». Учится только на том, что пользователь пишет Mico."""
        fixed, changes = self.typo.correct(q)
        fixed = phrase.canonical(fixed) or fixed                   # «давай помодоро!» → понятная форма
        self._handled = False
        r = self._ask(fixed)
        self.dialog.add("user", fixed)                                              # помним диалог, в том числе команды
        self.dialog.add("mico", r.text if r else "")
        try:
            self.typo.observe(q, fixed, handled=self._handled, changes=changes)     # учёба на опечатках
        except Exception:
            pass
        try:
            self.on_command(fixed)                                                  # учёт кнопок и команд
        except Exception:
            pass
        if changes and self._handled and r.text:
            r.text = typo.note(changes) + r.text
        return r

    def quick_answer(self, prompt, image_b64=None):
        """Короткий вопрос вне разговора (файл, буфер, ошибка, окно): ответ не попадает в память диалога.
        Картинка уходит только в локальную модель для изображений."""
        model = self.cfg["vision_model"] if image_b64 else self.cfg["text_model"]
        return self._chat(prompt, model, image_b64=image_b64)

    def _agent_call(self, name, args):
        """Действие на компьютере: всё, что меняет систему, выполняется только после «да»."""
        if osagent.needs_confirm(name):
            return commands._ask(f"Сделаю так: {osagent.describe(name, args)}.",
                                 lambda: self._run_action(name, args))
        return self._run_action(name, args)

    def _run_action(self, name, args):
        try:
            return Reply(osagent.execute(name, args, self.notify), "happy")
        except Exception as e:                                     # ошибка Windows не должна ронять чат
            return Reply(f"Не получилось: {e}", "worried")

    def _rewrite_followup(self, q):
        """Продолжение разговора модель переписывает как самостоятельную просьбу. None — не поняла."""
        handled = self._handled
        try:
            answer = self._chat(self.dialog.rewrite_prompt(q), self.cfg["text_model"])
        except requests.RequestException:
            return None
        finally:
            self._handled = handled
        return dialog.Dialog.clean_rewrite(answer, q)

    def _run_steps(self, steps):
        """Своя фраза: выполняем шаги по очереди обычным разбором команд."""
        texts, mood = [], "happy"
        for s in steps:
            r = commands.handle(s, self.notify, lambda: self.last_hwnd())
            if r is None:
                texts.append(f"Не понял шаг «{s}»")
                mood = "worried"
            else:
                texts.append(r.text)
                mood = r.mood
        self._handled = True
        return Reply("\n".join(t for t in texts if t), mood)

    def _plan(self, task):
        """«Подготовь рабочее место»: показываем план и выполняем только после «да»."""
        try:
            ok, dropped = planner.make_plan(task, lambda p: self._chat(p, self.cfg["text_model"], use_history=False))
        except (requests.RequestException, ValueError) as e:
            return Reply(f"Не получилось составить план: {e}. Опиши задачу проще или скажи шаги по одному.", "worried")
        if not ok:
            return Reply("Не придумал безопасного плана из того, что я умею. Попробуй описать шаги по одному.",
                         "curious")
        lines = [f"{i + 1}. {s}" for i, s in enumerate(ok)]
        note = ""
        if dropped:
            note = ("\n\nЯ убрал из плана: " + "; ".join(s for s, _ in dropped) +
                    ". Такие действия дай отдельной командой.")
        return commands._ask("План:\n" + "\n".join(lines) + note + "\n\nВыполнить?", lambda: self._run_plan(ok))

    def _run_plan(self, steps):
        texts, mood = [], "happy"
        for s in steps:
            r = commands.handle(s, self.notify, lambda: self.last_hwnd())
            if r is None:
                return Reply("\n".join(texts + [f"Не смог выполнить шаг «{s}» и остановился."]), "worried")
            texts.append(f"✓ {r.text}" if r.text else f"✓ {s}")
            mood = r.mood
        self._handled = True
        return Reply("\n".join(texts) or "План выполнен.", mood)

    def _personal_command(self, q, ql):
        """Заметки, помодоро, повторяющиеся напоминания, проверка окружения."""
        import recur
        rec = recur.parse(q)
        if rec and features.enabled("recurring", self.cfg):
            import reminders
            rule = recur.encode(rec["days"], rec["hour"], rec["minute"])
            due = recur.next_due(rec["days"], rec["hour"], rec["minute"])
            reminders.add(rec["text"], due, self.notify, rule)
            when = time.strftime("%d.%m в %H:%M", time.localtime(due))
            return Reply(f"Буду напоминать: «{rec['text']}». Ближайшее — {when}, дальше по этому расписанию.", "happy")
        n = notes.parse(q)
        if n:
            kind, value = n
            if kind == "add":
                self.store.add_note(time.time(), value)
                return Reply(f"Записал: «{value}». Скажи «что я записывал сегодня», чтобы посмотреть.", "happy")
            return Reply(notes.format_list(self.store.list_notes(), value), "happy")
        s = ql.strip()
        if features.enabled("pomodoro", self.cfg):
            intent = phrase.pomodoro_intent(q)                   # помодоро в любой форме, не только по точной фразе
            if intent == "start":
                ok = self.pomo.start()
                return Reply("Запускаю помодоро: 25 минут работы, потом напомню про перерыв."
                             if ok else "Помодоро уже идёт.", "happy")
            if intent == "stop":
                return Reply("Помодоро остановлен." if self.pomo.stop() else "Помодоро сейчас не идёт.", "happy")
            if intent == "status":
                return Reply(f"Сегодня завершено циклов помодоро: {self._pomo_today()}.", "happy")
        if re.fullmatch(r"(проверь (mico|мико|себя|окружение|настройки)|что не так|диагностика|проверка окружения)", s):
            return Reply(self.environment(), "curious")
        return None

    def _pomo_today(self):
        log = self.cfg.setdefault("pomodoro_log", {})
        return log.get(time.strftime("%Y-%m-%d"), 0)

    def _pomo_cycle(self):
        log = self.cfg.setdefault("pomodoro_log", {})
        day = time.strftime("%Y-%m-%d")
        log[day] = log.get(day, 0) + 1
        self.save_cfg()

    def environment(self):
        """Отчёт о том, всё ли готово к работе."""
        from diagnose import environment_report, ollama_probe
        import winctl                         # тяжёлые зависимости — только здесь
        checks = [
            ("Ollama и текстовая модель", ollama_probe(BASE, [self.cfg["text_model"]])),
            ("Модель для анализа экрана", ollama_probe(BASE, [self.cfg["vision_model"]])),
            ("Права администратора", lambda: (winctl.is_admin(),
                                             "нужны только для служб и компонентов Windows (появится запрос UAC)")),
        ]
        return environment_report(checks)

    def _windows_question(self, q, ql):
        """Вопросы про Windows: где настройка (и открыть её), какая версия и сборка, что нового."""
        import windows_compare as WC
        if re.search(r"сравни|что изменилось|разниц|отличаются|что нового между|что нового в .*версии", ql):
            return Reply(WC.answer_compare(q, WC.read_system()), "happy")
        if re.search(r"(моя|моей|мою|моё|текущ\w*)\s+(сборк|верси)|какая (у меня )?(сборка|версия)|"
                     r"версия windows|что нового в (windows|виндовс|сборк|версии)", ql):
            return Reply(WC.answer_current(WC.read_system()), "happy")
        if re.search(r"\b(где|как)\b", ql) and re.search(
                r"настро|найти|найди|открыть|включить|поменять|изменить|сменить|находится", ql):
            found = windows_info.find_setting(q)
            if found:
                title, path, uri = found
                windows_info.open_setting(uri)
                return Reply(f"Открыл «{title}»: {path}.", "happy")
        return None

    def _count_use(self, feature):
        """Считаем, сколько раз пользовались бета-функцией. Только число: ни текста, ни содержимого."""
        use = self.cfg.setdefault("beta_usage", {})
        use[feature] = use.get(feature, 0) + 1
        self.save_cfg()

    MANUAL_UPDATE = re.compile(r"есть ли (?:новая |новые )?верси\w* (?:mico|мико)"
                               r"|проверь (?:новую )?верси\w* (?:mico|мико)"
                               r"|проверь обновлени\w* (?:mico|мико)")

    def _manual_update(self, ql):
        """«Есть ли новая версия Mico?» — проверяем сейчас, не дожидаясь суточной проверки."""
        if not self.MANUAL_UPDATE.fullmatch(ql.strip(" .!?")):
            return None
        info = updatecheck.fetch_latest()
        if info is None:
            return Reply("Не смог проверить: нет связи с GitHub или релизов пока нет. Попробуй позже.", "worried")
        self.cfg["update_checked_at"] = time.time()
        self.save_cfg()
        remote = updatecheck.version_of(info["tag"])
        if not remote or not updatecheck.is_newer(remote, version.APP_VERSION):
            return Reply(f"Нет новой версии: у тебя последняя, {version.APP_VERSION} 👍", "happy")
        url = info["url"]
        return commands._ask(f"Вышла версия {remote}, у тебя {version.APP_VERSION}. Открыть страницу загрузки?",
                             lambda: (webbrowser.open(url), Reply("Открыл страницу загрузки 🔗", "happy"))[1])

    def _beta_command(self, q, ql):
        """Бета-функции: рабочее место, история копирования, итог дня. None — это не про них."""
        if features.enabled("workspace", self.cfg):
            kind = workspace.command(ql)
            if kind:
                self._count_use("workspace")
            if kind == "save":
                apps = workspace.save(self.cfg, W.visible_apps())
                self.save_cfg()
                if not apps:
                    return Reply("Не вижу открытых программ, которые можно запомнить 🤔", "curious")
                return Reply(f"Запомнил рабочее место: {workspace.names(apps)} 🗂", "happy")
            if kind == "restore":
                if not workspace.saved_apps(self.cfg):
                    return Reply("Рабочее место ещё не запомнено. Открой нужные программы и скажи «запомни рабочее место».",
                                 "curious")
                todo = workspace.plan_restore(self.cfg, W.running_names())
                if not todo:
                    return Reply("Всё запомненное уже открыто 👍", "happy")
                return commands._ask(f"Открыть {len(todo)}: {workspace.names(todo)}?",
                                     lambda: self._open_workspace(todo))
        if features.enabled("clipboard_search", self.cfg):
            c = clipbuf.command(ql)
            if c:
                self._count_use("clipboard_search")
                if c[0] == "forget":
                    self.store.forget_clips()
                    return Reply("Историю копирования очистил 🧹", "happy")
                query = c[1].lower()
                hits = [(ts, t) for ts, t in self.store.list_clips() if not query or query in t.lower()][:5]
                if not hits:
                    return Reply("Ничего не нашёл в истории копирования 🤔" if query
                                 else "История копирования пока пуста.", "curious")
                fmt_ts = lambda ts: time.strftime("%d.%m %H:%M", time.localtime(ts))
                return Reply("Вот что нашёл:\n" + clipbuf.format_hits(hits, fmt_ts), "happy")
        more = self._beta_more(q, ql)
        if more:
            return more
        if features.enabled("day_summary", self.cfg):
            d = daysum.command(ql)
            if d:
                self._count_use("day_summary")
                if d[0] == "schedule":
                    self.cfg["day_summary_at"] = d[1]
                    self.save_cfg()
                    if not d[1]:
                        return Reply("Хорошо, итог дня больше не присылаю 👌", "happy")
                    return Reply(f"Буду присылать итог дня в {d[1]} 🌙", "happy")
                return Reply(daysum.build(self.store, time.time()), "happy")
        return None

    def _beta_more(self, q, ql):
        """Вторая партия бета-функций: здоровье ПК, итог недели, список дел, очистка, порядок в загрузках, расписание."""
        if features.enabled("health", self.cfg) and health.command(ql):
            self._count_use("health")
            return Reply(health.report(W.disk_usage, W.boot_time(), time.time(), defender=W.defender_on()), "happy")
        if features.enabled("week_summary", self.cfg) and daysum.week_command(ql):
            self._count_use("week_summary")
            return Reply(daysum.week_text(self.store, time.time()), "happy")
        if features.enabled("todo", self.cfg):
            t = todo.command(ql)
            if t:
                self._count_use("todo")
                kind, arg = t
                if kind == "add":
                    self.store.add_todo(time.time(), arg)
                    return Reply(f"Добавил в список дел: {arg} ✏", "happy")
                if kind == "show":
                    return Reply(todo.render(self.store.list_todos()), "happy")
                if kind == "done":
                    hit = todo.find_open(self.store.list_todos(), arg)
                    if not hit:
                        return Reply("Не нашёл одно открытое дело с таким текстом 🤔", "curious")
                    self.store.set_todo_done(hit[0], True)
                    return Reply(f"Отметил выполненным: {hit[1]} ✔", "happy")
                if kind == "clear":
                    return Reply(f"Убрал выполненные дела: {self.store.clear_done_todos()} 🧹", "happy")
        if features.enabled("cleanup", self.cfg):
            c = cleanup.command(ql)
            if c == "size":
                self._count_use("cleanup")
                home = os.path.expanduser("~")
                folders = {n: cleanup.folder_size(os.path.join(home, n)) for n in ("Downloads", "Documents", "Videos", "Desktop")}
                folders["Временные файлы"] = cleanup.folder_size(cleanup.temp_dir())
                return Reply(cleanup.size_text(folders), "curious")
            if c == "clean":
                self._count_use("cleanup")
                files = cleanup.old_temp_files(cleanup.temp_dir(), time.time())
                if not files:
                    return Reply("Старых временных файлов нет — чистить нечего 👌", "happy")
                total = sum(s for _, s in files)
                return commands._ask(f"Удалить {len(files)} временных файлов старше суток ({cleanup._mb(total)})?",
                                     lambda: self._do_clean(files))
        if features.enabled("sorter", self.cfg):
            k = sorter.command(ql)
            if k == "sort":
                self._count_use("sorter")
                moves = sorter.plan(os.path.join(os.path.expanduser("~"), "Downloads"))
                if not moves:
                    return Reply("В «Загрузках» нечего раскладывать 👌", "happy")
                return commands._ask(f"Разложить {len(moves)} файлов по папкам в «Загрузках»? "
                                     "Потом можно сказать «отмени сортировку»", lambda: self._do_sort(moves))
            if k == "undo":
                self._count_use("sorter")
                done = self.cfg.get("last_sort") or []
                if not done:
                    return Reply("Нечего отменять.", "curious")
                back = sorter.undo([tuple(p) for p in done])
                self.cfg["last_sort"] = []
                self.save_cfg()
                return Reply(f"Вернул на места файлов: {back} ↩", "happy")
        if features.enabled("schedule", self.cfg):
            low = ql.replace("ё", "е")
            if re.fullmatch(r"(покажи|какие\s+у\s+меня)\s+расписани\w*|мои\s+расписани\w*", low.strip(" .!?")):
                self._count_use("schedule")
                rules = self.cfg.get("schedules") or []
                return Reply("\n".join(f"• {r['action']} в {r['at']}" for r in rules) or "Расписаний нет.", "happy")
            if re.fullmatch(r"(удали|очисти)\s+(все\s+)?расписани\w*", low.strip(" .!?")):
                self.cfg["schedules"] = []
                self.save_cfg()
                return Reply("Расписания удалил 🧹", "happy")
            rules = schedule.parse(low, self._schedulable)
            if rules:
                self._count_use("schedule")
                self.cfg["schedules"] = (self.cfg.get("schedules") or []) + [
                    {"action": a, "at": at, "last": ""} for a, at in rules]
                self.save_cfg()
                text = "; ".join(f"«{a}» в {at}" for a, at in rules)
                return Reply(f"Запланировал: {text} ⏰", "happy")
        return None

    def _schedulable(self, action):
        """Можно ли поставить действие в расписание: это переключатель без подтверждения или тема."""
        if re.search(r"тем", action):
            return True
        t = components.find_toggle(action)
        if not t or t.admin or t.confirm_on or t.confirm_off:
            return False                          # права администратора и подтверждения — только вручную
        return not re.search(r"защит|брандмауэр|файрвол|удал[её]нн\w+ рабоч|служб", t.name.lower())   # безопасность — только вручную

    def _do_clean(self, files):
        done, freed, skipped = cleanup.delete_files(files)
        return Reply(f"Удалил {done} файлов, освободил {cleanup._mb(freed)}" +
                     (f", пропустил занятых: {skipped}" if skipped else "") + " 🧹", "happy")

    def _do_sort(self, moves):
        done, skipped = sorter.apply(moves)
        self.cfg["last_sort"] = [list(p) for p in done]
        self.save_cfg()
        return Reply(f"Разложил файлов: {len(done)}" + (f", пропустил занятых: {skipped}" if skipped else "")
                     + ". Чтобы вернуть, скажи «отмени сортировку» 📁", "happy")

    def _open_workspace(self, apps):
        opened = 0
        for a in apps:
            try:
                W.launch(a["exe"])
                opened += 1
            except OSError:
                pass
        return Reply(f"Открыл {opened} из {len(apps)} 🗂", "happy")

    def _ask(self, q, rewritten=False):
        ql = q.lower()
        if self.cfg.get("memory_on", True) and q.strip() and not rewritten:      # учимся на том, что пользователь просит
            try:
                self.store.add_action(time.time(), q.strip())
            except Exception:
                pass
        if phrase.is_greeting(q):                                # «доброе утро!», «привет 😊»
            return Reply(phrase.greeting_text(kind=phrase.greeting_kind(q)), "happy")
        remembered = self._recall(q)                             # «о чём мы говорили вчера»
        if remembered:
            return remembered
        refusal = smart.safety_refusal(ql)                       # опасное — не выполняем, объясняем
        if refusal:
            return Reply(refusal, "curious")
        calc = smart.calculate(q)                                # «сколько будет 17 умножить на 23»
        if calc:
            return Reply(calc, "happy")
        if smart.is_intro_question(ql):                          # «ты кто?»
            return Reply(smart.INTRO, "happy")
        if smart.is_toggle_question(ql):                         # «какие настройки ты умеешь переключать?»
            return Reply(smart.toggles_overview(components.TOGGLES), "happy")
        bare = smart.bare_verb_question(q)                       # «выключи» без объекта — уточняем
        if bare:
            return Reply(bare, "curious")
        small = smart.smalltalk(q)                               # «спасибо», «ты молодец», «мне грустно»
        if small:
            return Reply(small[0], small[1])
        steps = custom.find(q, self.cfg.get("custom_phrases", []))
        if steps:
            return self._run_steps(steps)
        ident = identity.answer(q)                               # кто тебя создал?
        if ident:
            return ident
        upd = self._manual_update(ql)                            # есть ли новая версия Mico?
        if upd:
            return upd
        beta = self._beta_command(q, ql)                         # бета: рабочее место, копирование, итог дня
        if beta:
            return beta
        if planner.wants_plan(q) and features.enabled("planner", self.cfg):
            return self._plan(q)
        sysreply = self._windows_question(q, ql)
        if sysreply:
            return sysreply
        personal = self._personal_command(q, ql)
        if personal:
            return personal
        try:
            if re.search(r"что (ты )?(умеешь|можешь)|помощь|^команды", ql):
                return Reply(capabilities.plain_capabilities(self.cfg), "happy", html=capabilities.html_capabilities(self.cfg))
            if self.is_screenshot(q):
                return actions.screenshot()
            r = commands.handle(q, self.notify, lambda: self.last_hwnd())   # Windows, приложения, сайты, таймеры…
            if r:
                self._handled = True
                return r
            if not rewritten:                                    # «погромче», «врубай вайфай» → известная команда
                better = intent.match(q)                         # без обращения к модели
                if better and better.strip().lower() != q.strip().lower():
                    return self._ask(better, rewritten=True)
            cap = smart.capability_question(ql)                  # «а ты умеешь музыку включать?»
            if cap:
                return Reply(cap, "happy")
            if "буфер" in ql:
                return self._clipboard(ql)
            if re.search(r"назад|что я делал|за последн", ql):
                return self._timeline(q)
            if "ответ" in ql and re.search(r"друг|подруг|сообщ|переписк|чат", ql):
                return self._screen("На экране переписка. Прочитай контекст и предложи 3 живых варианта "
                                    "ответа: дружеский, короткий, шутливый. Только варианты, без пояснений.")
            if re.search(r"на экране|экран|что я вижу|что это", ql):
                return self._screen(q + "\nОпиши кратко, что видно на экране, и ответь на вопрос.")
            if re.search(r"\b(как|что такое|что значит|почему|зачем|чем|какой|какая|какие)\b", ql):
                if self._kb is None:
                    self._kb = knowledge.load()
                kb = knowledge.answer(q, self._kb)           # проверенная статья — без обращения к модели
                if kb:
                    return Reply(kb, "happy")
            if not rewritten and self.dialog.is_followup(q):       # «а если больше» — сначала понимаем, о чём речь
                better = self._rewrite_followup(q)
                if better:
                    return self._ask(better, rewritten=True)
            raw = self._chat(q, self.cfg["text_model"], use_history=True, mood_tag=True,
                             tools=self.cfg.get("os_agent_on", True))
            try:
                call = osagent.parse(raw) if self.cfg.get("os_agent_on", True) else None
            except ValueError as e:
                return Reply(f"Не получилось: {e}. Скажи, что сделать, проще.", "worried")
            if call:
                return self._agent_call(*call)                     # модель выбрала действие на компьютере
            mood, ans = split_mood(raw)
            return Reply(ans, mood or detect_emotion(ans) or detect_emotion(q) or "idle")
        except requests.RequestException as e:
            return Reply(diagnose.explain_model_error(e, self.cfg["text_model"]), "sad")
