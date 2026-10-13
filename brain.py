"""Мозг Mico: локальные модели через Ollama (только 127.0.0.1) + маршрутизация запросов."""
import base64, html as html_mod, io, json, re, time
import mss, requests, win32gui
from PIL import Image
import actions, capabilities, commands, components, custom, dialog, diagnose, features, identity, indexer, knowledge, notes, osagent, planner, pomodoro, typo, windows_info
from actions import Reply
from emotions import detect_emotion, split_mood

BASE = "http://127.0.0.1:11434"
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
        self.dialog = dialog.Dialog(window=self.cfg.get("dialog_memory_min", 15) * 60)   # память диалога
        self.notify = lambda text: None
        self.last_hwnd = lambda: self.tracker.last_hwnd      # main.py заменит на окно из WindowWatcher
        extra = {w for t in components.TOGGLES for k in t.keys for w in k.split() if len(w) >= 4}
        self.typo = typo.Corrector(store, extra)               # опечатки и свой словарь
        self.on_command = lambda q: None                       # main.py: учёт кнопок и команд
        self.start_index = lambda: False                       # main.py: запуск индексации в фоне
        self._idx = None                                       # кэш индекса (расшифрованный)
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
        r = requests.post(BASE + "/api/chat", json={"model": model, "messages": messages, "stream": False},
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
        if "переведи" in ql:
            task = "Переведи на русский (если текст уже русский — на английский). Только перевод."
        elif "исправ" in ql:
            task = "Исправь ошибки в тексте. Только исправленный текст."
        elif re.search(r"кратко|суть", ql):
            task = "Перескажи кратко."
        else:
            task = "Объясни, что это, и кратко ответь по существу."
        out, mood = self._tagged(self._chat(task + "\n\n" + text[:6000], self.cfg["text_model"], mood_tag=True), "happy")
        return Reply(out, mood)

    def ask(self, q):
        """Понимает опечатки: «открй» → «открой». Учится только на том, что пользователь пишет Mico."""
        fixed, changes = self.typo.correct(q)
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
        pomo_on = features.enabled("pomodoro", self.cfg)
        if pomo_on and re.fullmatch(r"(помодоро|запусти помодоро|начни помодоро|pomodoro)", s):
            ok = self.pomo.start()
            return Reply("Запускаю помодоро: 25 минут работы, потом напомню про перерыв."
                         if ok else "Помодоро уже идёт.", "happy")
        if pomo_on and re.search(r"(стоп|останови|отмени|выключи) помодоро", s):
            return Reply("Помодоро остановлен." if self.pomo.stop() else "Помодоро сейчас не идёт.", "happy")
        if pomo_on and re.search(r"сколько помодоро|помодоро сегодня", s):
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
            ("Индекс компьютера", lambda: (bool(self.index_records()), "скажи «проиндексируй компьютер»")),
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

    def index_records(self):
        if self._idx is None:
            self._idx = self.store.load_index()
        return self._idx

    def _index_reply(self, q):
        """Ответ из индекса компьютера или None, если там ничего не нашлось."""
        recs = self.index_records()
        if not recs:
            return None
        hits = indexer.search(q, recs)
        if not hits:
            return None
        names = {"photo": "фото", "video": "видео", "music": "музыка", "document": "документ",
                 "game": "игра", "app": "программа", "folder": "папка"}
        rows = [f'<a href="mico-open:{h["path"]}">{html_mod.escape(h["name"])}</a> '
                f'<span style="color:#8a7d6a">({names.get(h["kind"], h["kind"])})</span>' for h in hits]
        text = f"Нашёл {len(hits)}:\n" + "\n".join(h["name"] for h in hits)
        return Reply(text, "happy", html=f"Нашёл {len(hits)}:<br>" + "<br>".join(rows))

    def _index_command(self, ql):
        if re.search(r"статус|как|сколько|идет|идёт|готов", ql) and "проиндексир" not in ql:
            return Reply(indexer.status_text(), "curious")
        if self.start_index():
            return Reply("Начинаю индексацию: программы, игры, папки, фото, документы, музыка и видео. "
                         "Прогресс будет под чатом. Имена и пути, содержимое файлов не читаю.", "thinking")
        return Reply(f"Индексация уже идёт. {indexer.status_text()}", "curious")

    def translate(self, text):
        """Перевод текста (для горячей клавиши на выделенном тексте)."""
        task = "Переведи на русский (если текст уже русский — на английский). Только перевод."
        return self._chat(task + "\n\n" + text[:6000], self.cfg["text_model"])

    def _ask(self, q, rewritten=False):
        ql = q.lower()
        if self.cfg.get("memory_on", True) and q.strip() and not rewritten:      # учимся на том, что пользователь просит
            try:
                self.store.add_action(time.time(), q.strip())
            except Exception:
                pass
        steps = custom.find(q, self.cfg.get("custom_phrases", []))
        if steps:
            return self._run_steps(steps)
        ident = identity.answer(q)                               # кто тебя создал?
        if ident:
            return ident
        if planner.wants_plan(q) and features.enabled("planner", self.cfg):
            return self._plan(q)
        if re.search(r"проиндексир|индексаци|индекс\b|как идет индекс|как идёт индекс", ql):
            return self._index_command(ql)
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
            if re.search(r"\b(найди|найти|поищи|ищи|искать|где|покажи|какие|какой|какая)\b", ql):
                r = self._index_reply(q)                 # сначала — по индексу компьютера
                if r:
                    return r
            if re.search(r"\b(найди|найти|поищи|ищи|искать)\b", ql) and re.search(FILEWORDS, ql):
                return actions.find_files(ql)
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
