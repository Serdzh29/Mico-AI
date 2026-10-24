"""Мозг Mico AI: локальные модели через Ollama (только 127.0.0.1) + маршрутизация запросов."""
import base64, io, json, os, re, threading, time, webbrowser
import mss, requests, win32gui
from PIL import Image
import guard, actions, capabilities, cleanup, clipbuf, clipcheck, commands, components, custom, dialog, diagnose, features, health, identity, knowledge, notes, osagent, phrase, smart, planner, pomodoro, schedule, sorter, typo, hogs, errhelp, updatecheck, version, windows_info, workspace, recall, intent, chatdigest
import winctl as W
import local_llm, model_catalog, model_store

BACKEND = {"name": "ollama"}           # «ollama» или «builtin» (встроенная модель без Ollama); main задаёт при запуске


def set_backend(name):
    BACKEND["name"] = "builtin" if name == "builtin" else "ollama"
from actions import Reply
from emotions import detect_emotion, for_reply, split_mood

BASE = "http://127.0.0.1:11434"
KEEP_ALIVE = "1m"                         # сколько модель держится в памяти после последнего вопроса: меньше — меньше RAM
SYSTEM = ("Ты — Mico AI, милый дружелюбный ИИ-компаньон на рабочем столе. Отвечай кратко и тепло, "
          "по-русски, если не просят иначе. Все данные остаются на этом ПК.")
MOOD_RULE = (" Начни ответ с одной метки настроения в квадратных скобках. Выбери ту, что ближе всего к тому, "
             "что ты чувствуешь прямо сейчас (не ставь [happy] только за дружелюбный тон — радость, когда есть повод): [happy] радость и дружелюбие; [love] тепло и нежность; [sad] грусть или "
             "сочувствие; [surprised] удивление; [laugh] смех; [curious] любопытство, интерес; [worried] тревога, "
             "беспокойство за человека; [scared] испуг; [angry] злость или раздражение; [shy] смущение; "
             "[confused] растерянность, непонимание; [excited] восторг, азарт; [proud] гордость за человека или "
             "его успех; [playful] озорство, шутка, подмигивание; [thinking] размышляю; [sleepy] усталость; "
             "[idle] спокойно и ровно. Сразу после метки — сам ответ. Метку нельзя пропускать.")
FILEWORDS = (r"файл|папк|документ|фото|картинк|изображен|видео|pdf|word|excel|презентац|таблиц|скачан|"
             r"на компьютере|на пк|на диске")
TEXT_MODEL_BIG = model_catalog.OLLAMA_TIERS[1]["id"]                      # 16 ГБ и больше: умнее, на русском хорошо
TEXT_MODEL_SMALL = model_catalog.OLLAMA_TIERS[0]["id"]                    # лёгкий режим (8 ГБ и меньше): быстро, отвечает по-русски хорошо, без рассуждений


def recommended_text_model():
    """Модель для общения по объёму памяти: 14 ГБ и больше — крупная, меньше — лёгкая."""
    try:
        import psutil
        gb = psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        gb = 8.0
    return TEXT_MODEL_BIG if gb >= 14 else TEXT_MODEL_SMALL


SUGGEST_TEXT = [TEXT_MODEL_BIG, TEXT_MODEL_SMALL, "qwen2.5:7b", "qwen2.5:14b", "deepseek-r1:7b", "deepseek-r1:8b", "deepseek-r1:14b",
                 "llama3.2:3b", "llama3.1:8b", "gemma2:9b", "phi4",
                 "qwen3-coder", "gpt-oss:20b", "glm-4.7-flash"]     # рекомендованные Ollama модели для программ-агентов
VISION_MODELS = ["qwen2.5vl:3b", "qwen2.5vl:7b", "llava:7b", "gemma3:4b"]   # модели для экрана: скачиваются и выбираются в настройках
VISION_MODEL = "qwen2.5vl:7b"             # модель для экрана по умолчанию
SUGGEST_VISION = VISION_MODELS


def chat_tiers():
    """Модели для чата, которые мы подобрали под каждый объём памяти. Других в списке скачивания нет.
    Встроенный режим — из каталога (без устаревших); режим Ollama — две модели: лёгкая и крупная."""
    if BACKEND["name"] == "builtin":
        return [{"id": m["id"], "label": f"{m['title']} ({m['quant']})", "min_ram_gb": m["min_ram_gb"]}
                for m in model_catalog.CATALOG if not m.get("legacy") and m.get("kind") != "vision"]
    return [{"id": t["id"], "label": t["title"], "min_ram_gb": t["min_ram_gb"]} for t in model_catalog.OLLAMA_TIERS]


def recommended_chat_id(ram_gb=None):
    """Модель, которую советуем для этого объёма памяти: самая крупная из подходящих, а если память мала — самая лёгкая."""
    if ram_gb is None:
        try:
            import psutil
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        except Exception:
            ram_gb = 8.0
    tiers = sorted(chat_tiers(), key=lambda t: t["min_ram_gb"])
    fitting = [t for t in tiers if ram_gb + model_catalog.MEMORY_SLACK_GB >= t["min_ram_gb"]]
    return (fitting[-1] if fitting else tiers[0])["id"]


def is_vision_model(name):
    """Модель для экрана: из списка Mico или по имени (vl, llava, vision…). Остальные — для чата."""
    n = str(name or "").lower()
    return n in VISION_MODELS or bool(re.search(r"vl|llava|vision|moondream|minicpm-v", n))


def list_models():
    if BACKEND["name"] == "builtin":                       # встроенный режим: что уже скачано из каталога
        return model_store.installed_ids()
    try:
        return sorted(m["name"] for m in requests.get(BASE + "/api/tags", timeout=5).json().get("models", []))
    except Exception:
        return []


def delete_model(name):
    """Удаляет модель из Ollama и освобождает место на диске. True — удалена."""
    if BACKEND["name"] == "builtin":
        return model_store.delete(name)
    try:
        r = requests.delete(BASE + "/api/delete", json={"model": name}, timeout=60)
        return r.status_code == 200
    except requests.RequestException:
        return False


REGISTRY = "https://registry.ollama.ai/v2"          # реестр, откуда Ollama качает модели


def model_layer_sizes(name, timeout=8):
    """Все слои модели с размерами из манифеста реестра — чтобы полоска знала общий размер сразу.
    Ollama в потоке сообщает размер слоя только тогда, когда начинает его качать, поэтому без манифеста
    итог растёт рывками. None — манифест не получили (нет сети или имя не найдено); тогда считаем по потоку."""
    try:
        base, _, tag = name.partition(":")
        if "/" not in base:
            base = "library/" + base
        r = requests.get(f"{REGISTRY}/{base}/manifests/{tag or 'latest'}", timeout=timeout,
                         headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"})
        r.raise_for_status()
        manifest = r.json()
        sizes = {layer["digest"]: int(layer["size"]) for layer in manifest.get("layers", [])}
        if manifest.get("config"):
            sizes[manifest["config"]["digest"]] = int(manifest["config"]["size"])
        return sizes or None
    except Exception:
        return None


def pull_model(name, cb, progress=None):
    if BACKEND["name"] == "builtin":                       # скачиваем GGUF из каталога, без Ollama
        entry = model_catalog.by_id(name)
        if entry is None:
            cb(f"Модели «{name}» нет в каталоге Mico AI")
            return False
        cb(f"Скачиваю {entry['title']}…")
        ok = model_store.download(name, progress)
        cb("Готово" if ok else "Не получилось скачать. Нажми «Скачать» ещё раз — загрузка продолжится.")
        return ok
    """Скачивание модели через локальный Ollama; cb(строка статуса). Возвращает True/False.
    progress(скачано_байт, всего_байт) — для полоски. Всё, что скачано, не больше размера модели
    и не отрицательно. Ollama докачивает с места остановки, поэтому при обрыве связи пробуем ещё раз.
    Успехом считается только статус «success»: если поток оборвался раньше, об этом говорим прямо."""
    sizes = model_layer_sizes(name)
    layers = {digest: (0, size) for digest, size in (sizes or {}).items()}   # слой → (скачано, размер)

    def report():
        if progress:
            progress(sum(c for c, _t in layers.values()), sum(t for _c, t in layers.values()))
    report()
    reason = "соединение прервалось"
    for attempt in range(3):
        try:
            # тайм-аут: если поток молчит 5 минут, это обрыв, а не загрузка — иначе окно висит вечно
            with requests.post(BASE + "/api/pull", json={"model": name, "name": name, "stream": True},
                               stream=True, timeout=(10, 300)) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    d = json.loads(line)
                    if d.get("error"):
                        cb("Ошибка: " + d["error"])
                        return False
                    if d.get("status") in ("verifying sha256 digest", "writing manifest"):
                        cb("проверяю…")                        # Ollama сама сообщила, что проверяет файлы
                    if d.get("status") == "success":          # Ollama закончила: все слои целиком
                        layers = {k: (t, t) for k, (_c, t) in layers.items()}
                        report()
                        return True
                    if d.get("total"):
                        key = d.get("digest") or d.get("status", "")
                        prev_done, prev_total = layers.get(key, (0, 0))
                        total = prev_total if key in layers else max(prev_total, int(d["total"]))
                        # строки слоя могут повторяться или откатываться — берём максимум, но не больше размера
                        done = min(max(prev_done, int(d.get("completed", 0) or 0), 0), total)
                        layers[key] = (done, total)
                        report()
        except requests.ConnectionError:
            cb("Ошибка: не получилось подключиться к движку моделей. Он запущен?")
            return False
        except Exception as e:
            reason = str(e) or reason
        if attempt < 2:
            cb(f"Связь прервалась, докачиваю ({attempt + 2} из 3)…")
            time.sleep(3)
    cb(f"Скачивание не дошло до конца: {reason}. Нажми «Скачать» ещё раз — загрузка продолжится с того же места.")
    return False

SUMMARY_EVERY = 6                     # сколько реплик между обновлениями сводки чата

class Brain:
    last_screen = None                  # (картинка в base64, время) — последний снимок экрана для вопросов по нему
    def __init__(self, cfg, store, tracker):
        self.cfg, self.store, self.tracker = cfg, store, tracker
        self.dialog = dialog.Dialog(window=self.cfg.get("dialog_memory_min", 15) * 60,   # память диалога
                                    persist=self._persist_turn)                          # и журнал на диске
        self.notify = lambda text: None
        self.conv_id = None                                   # открытый чат (см. set_conversation)
        self.conv_summary = ""                                # суть открытого чата: её помнит Mico AI
        self._since_summary = 0                               # реплик с последней сводки
        self._summary_busy = False
        self.last_hwnd = lambda: self.tracker.last_hwnd      # main.py заменит на окно из WindowWatcher
        extra = {w for t in components.TOGGLES for k in t.keys for w in k.split() if len(w) >= 4}
        self.typo = typo.Corrector(store, extra)               # опечатки и свой словарь
        self.on_command = lambda q: None                       # main.py: учёт кнопок и команд
        self._kb = None                                        # база знаний Mico AI (статьи из knowledge/)
        self.save_cfg = lambda: None                           # main.py: сохранить настройки
        self.pomo = pomodoro.Pomodoro(lambda t: self.notify(t), self._pomo_cycle)
        self._handled = False

    def _builtin_screen(self, prompt, image_b64):
        """Экран без Ollama: модель для экрана и её проектор картинки из каталога."""
        vid = self.cfg.get("vision_model")
        entry = model_catalog.by_id(vid or "")
        if not entry or entry.get("kind") != "vision":
            vid = model_catalog.VISION_ID                        # в настройках стоит модель Ollama — берём встроенную
        model_path = model_store.path_for(vid)
        mm_path = model_store.mmproj_path_for(vid)
        if not (model_path and os.path.isfile(model_path) and mm_path and os.path.isfile(mm_path)):
            raise local_llm.LocalModelError("Модель для экрана не скачана. Скачай её в ⚙ Настройки → Модели.")
        text = local_llm.describe_image(model_path, mm_path, prompt, image_b64)
        return guard.reply_guard(text.strip())

    def _chat(self, user, model, image_b64=None, use_history=False, mood_tag=False, tools=False):
        msg = {"role": "user", "content": user}
        if image_b64:
            msg["images"] = [image_b64]
        system = SYSTEM + ((MOOD_RULE + self._variety_hint()) if mood_tag else "") + ("\n" + osagent.prompt() if tools else "")
        if use_history and self.conv_summary:                 # суть открытого чата — чтобы помнить разговор целиком
            system += f"\n\nСуть этого разговора, которую ты помнишь: {self.conv_summary}"
        if use_history:
            system += self._profile_note()                     # имя и «о себе» из профиля — для персонализации
        messages = ([{"role": "system", "content": system}] +
                    (self.dialog.messages(limit=8) if use_history else []) + [msg])
        if BACKEND["name"] == "builtin":
            if image_b64:
                return self._builtin_screen(user, image_b64)
            path = model_store.path_for(model)
            if not path or not os.path.isfile(path):
                raise local_llm.LocalModelError(f"Модель «{model}» не скачана. Скачай её в ⚙ Настройки → Модели.")
            text = local_llm.chat(path, messages)
            return guard.reply_guard(text.strip())
        # Qwen3 по умолчанию пишет длинные рассуждения и отвечает очень медленно: для чата их выключаем
        # (и через параметр think, и просьбой /no_think в тексте вопроса). Ответ короче — быстрее.
        thinks = "qwen3" in str(model).lower() and not image_b64
        if thinks:
            messages = local_llm._no_think(messages)
        payload = {"model": model, "messages": messages, "stream": False,
                   "keep_alive": 0 if image_b64 else KEEP_ALIVE,     # после экрана модель сразу выгружается из памяти, после текста — через минуту
                   "options": {"num_predict": local_llm.MAX_TOKENS}}
        if thinks:
            payload["think"] = False
        r = requests.post(BASE + "/api/chat", json=payload, timeout=300)
        r.raise_for_status()
        text = r.json()["message"]["content"]
        # DeepSeek-R1 пишет рассуждения в блоке <think>…</think>: их пользователю не показываем
        text = local_llm.clean_reply(text)
        return guard.reply_guard(text.strip())     # запрещённое и мат — до показа

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

    def _variety_hint(self):
        """Чтобы лицо Mico не застывало: модель знает, какие настроения были недавно, и не повторяет их без причины."""
        recent = getattr(self, "_recent_moods", [])[-3:]
        if len(recent) >= 2 and len(set(recent)) == 1:
            return (f" Последние ответы были с настроением [{recent[-1]}] — в этот раз выбери другое, "
                    "если оно тоже подходит по смыслу.")
        if recent:
            return f" Недавно были настроения: {', '.join(recent)}. Не повторяй одно и то же без причины."
        return ""

    @staticmethod
    def _tagged(raw, default=None):
        """Ответ модели с меткой настроения → (текст, эмоция). Без метки — эмоция по смыслу текста."""
        mood, text = split_mood((raw or "").strip())
        text = text.strip()
        return text, mood or detect_emotion(text) or default or for_reply(text)

    def _screen(self, prompt):
        if self.tracker.last_blocked:
            return Reply("Это окно в списке исключений (пароли/приватный режим), я его не смотрю 🙈", "worried")
        shot = self._screenshot_b64()
        self.last_screen = (shot, time.time())          # снимок помним: следующие вопросы про экран получат его
        text, mood = self._tagged(self._chat(prompt, self.cfg["vision_model"], shot, mood_tag=True), "curious")
        return Reply(text, mood)

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
        out, mood = self._tagged(self._chat(task + "\n\n" + text[:6000], self.cfg["text_model"], mood_tag=True))
        return Reply(out, mood)

    def _profile_note(self):
        """Что Mico AI знает о пользователе (из профиля). Пусто, если профиль не заполнен."""
        name = " ".join(str(self.cfg.get("user_name", "")).split())
        about = str(self.cfg.get("user_about", "")).strip()
        if not name and not about:
            return ""
        parts = []
        if name:
            parts.append(f"Пользователя зовут {name}; обращайся по имени, когда это уместно.")
        if about:
            parts.append("О нём: " + about[:600])
        return "\n\n" + " ".join(parts)

    def set_conversation(self, conv_id):
        """Открыли чат (или новый: None). Mico AI помнит реплики и суть открытого чата, а не только последние минуты."""
        self.conv_id = conv_id
        self._since_summary = 0
        if conv_id is None:
            self.dialog.clear()
            self.conv_summary = ""
            return
        rows = self.store.conv_messages(conv_id, limit=12)
        self.dialog.restore([(ts, "user" if r == "user" else "mico", t) for _, ts, r, t in rows])
        self.conv_summary = self.store.conv_summary(conv_id)

    def after_turn(self, conv_id):
        """Вызывается после каждого ответа. Раз в несколько реплик обновляет сводку чата — в фоне, не задерживая ответ."""
        self._since_summary += 1
        if conv_id is None or conv_id != self.conv_id or self._since_summary < SUMMARY_EVERY or self._summary_busy:
            return
        self._since_summary = 0
        self._summary_busy = True

        def work():
            try:
                rows = self.store.conv_messages(conv_id, limit=24)
                lines = "\n".join(("Пользователь: " if r == "user" else "Mico AI: ") + t[:300] for _, _, r, t in rows)
                prev = self.store.conv_summary(conv_id) or "—"
                prompt = ("Прежняя сводка разговора:\n" + prev + "\n\nПоследние реплики:\n" + lines +
                          "\n\nНапиши обновлённую сводку разговора в 3–5 предложениях по-русски: о чём говорили, "
                          "что решили, что важно помнить о человеке и его делах. Только сводка, без вступления.")
                text = (self._chat(prompt, self.cfg["text_model"]) or "").strip()
                if text and conv_id == self.conv_id:
                    self.store.conv_set_summary(conv_id, text)
                    self.conv_summary = text
            except Exception:
                pass                                          # сводка — не главное: ошибка не должна мешать чату
            finally:
                self._summary_busy = False
        threading.Thread(target=work, daemon=True).start()

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
        time.sleep(90)                                   # даём Mico AI открыться и модели прогреться
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
        if r is not None and getattr(r, "mood", None):
            self._recent_moods = (getattr(self, "_recent_moods", []) + [r.mood])[-6:]     # помним, чтобы не повторять
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
            return Reply(osagent.execute(name, args, self.notify), None)
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
            return Reply(f"Буду напоминать: «{rec['text']}». Ближайшее — {when}, дальше по этому расписанию.", None)
        n = notes.parse(q)
        if n:
            kind, value = n
            if kind == "add":
                self.store.add_note(time.time(), value)
                return Reply(f"Записал: «{value}». Скажи «что я записывал сегодня», чтобы посмотреть.", None)
            if kind == "search":
                found = notes.search(value, self.store.list_notes(limit=2000))
                return Reply(notes.format_search(value, found), None)
            return Reply(notes.format_list(self.store.list_notes(), value), None)
        s = ql.strip()
        if features.enabled("pomodoro", self.cfg):
            intent = phrase.pomodoro_intent(q)                   # помодоро в любой форме, не только по точной фразе
            if intent == "start":
                ok = self.pomo.start()
                return Reply("Запускаю помодоро: 25 минут работы, потом напомню про перерыв."
                             if ok else "Помодоро уже идёт.", None)
            if intent == "stop":
                return Reply("Помодоро остановлен." if self.pomo.stop() else "Помодоро сейчас не идёт.", None)
            if intent == "status":
                return Reply(f"Сегодня завершено циклов помодоро: {self._pomo_today()}.", None)
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
            ("Движок и текстовая модель", ollama_probe(BASE, [self.cfg["text_model"]])),
            ("Модель для анализа экрана", ollama_probe(BASE, [self.cfg["vision_model"]])),
            ("Права администратора", lambda: (winctl.is_admin(),
                                             "нужны только для служб и компонентов Windows (появится запрос UAC)")),
        ]
        return environment_report(checks)

    def _hogs_question(self):
        """«Что тормозит компьютер?» — самая заметная программа и предложение закрыть её, только по подтверждению."""
        import hogs
        self._count_use("hogs")
        top = hogs.pick(hogs.sample())
        if not top:
            return Reply("Сейчас ничего не тормозит: процессор и память в норме 👌", None)
        target = top[0]
        lines = "\n".join("• " + hogs.describe(x) for x in top)

        def close():
            if hogs.close_gently(target["pid"]):
                return Reply(f"Попросил «{target['name']}» закрыться. Если там есть несохранённое, "
                             "программа сама спросит 🙂", None)
            return Reply(f"У «{target['name']}» нет окон, которые можно закрыть вежливо. Оставляю как есть.",
                         "curious")
        return commands._ask(f"Больше всего сейчас нагружает:\n{lines}\nЗакрыть «{target['name']}»?", close)

    def _errhelp_question(self, kind):
        """«Покажи журнал» — последние строки журнала Mico AI.
        «Найди решение» — Mico AI сам разбирает последнюю ошибку и отвечает шагами. Другие приложения не открывает."""
        import errhelp
        self._count_use("errhelp")
        if kind == "log":
            name, text = errhelp.log_tail()
            if not text:
                return Reply("Журнала ошибок пока нет: Mico AI ничего не записывал 👌", None)
            return Reply(f"Последние строки из {name}:\n\n{text}", "curious")
        ctx = errhelp.last_error()
        if ctx is None:
            name, text = errhelp.log_tail()
            if not text:
                return Reply("Не вижу ошибки. Открой окно с ошибкой или скопируй текст ошибки, и я найду решение.",
                             "curious")
            ctx = (name, text)
        title, text = ctx
        answer = self._chat(errhelp.solution_prompt(title, text), self.cfg["text_model"])
        return Reply(answer or "Не получилось найти решение. Попробуй ещё раз или скопируй текст ошибки.", "curious")

    def _windows_question(self, q, ql):
        """Вопросы про Windows: какая версия и сборка, где настройка (и открыть её)."""
        if re.search(r"(моя|моей|мою|моё|текущ\w*)\s+(сборк|верси)|какая (у меня )?(сборка|версия)|версия windows", ql):
            build, ubr = windows_info.current_build()
            if build is None:
                return Reply("Не смог прочитать версию Windows на этом компьютере.", "worried")
            tail = f".{ubr}" if ubr is not None else ""
            return Reply(f"Сейчас у тебя {windows_info.version_of(build)}, сборка {build}{tail}.", None)
        if re.search(r"\b(где|как)\b", ql) and re.search(
                r"настро|найти|найди|открыть|включить|поменять|изменить|сменить|находится", ql):
            found = windows_info.find_setting(q)
            if found:
                title, path, uri = found
                windows_info.open_setting(uri)
                return Reply(f"Открыл «{title}»: {path}.", None)
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
        """«Есть ли новая версия Mico AI?» — проверяем сейчас, не дожидаясь суточной проверки."""
        if not self.MANUAL_UPDATE.fullmatch(ql.strip(" .!?")):
            return None
        info = updatecheck.fetch_latest()
        if info is None:
            return Reply("Не смог проверить: нет связи с GitHub или релизов пока нет. Попробуй позже.", "worried")
        self.cfg["update_checked_at"] = time.time()
        self.save_cfg()
        remote = updatecheck.version_of(info["tag"])
        if not remote or not updatecheck.is_newer(remote, version.APP_VERSION):
            return Reply(f"Нет новой версии: у тебя последняя, {version.APP_VERSION} 👍", None)
        url = info["url"]
        return commands._ask(f"Вышла версия {remote}, у тебя {version.APP_VERSION}. Открыть страницу загрузки?",
                             lambda: (webbrowser.open(url), Reply("Открыл страницу загрузки 🔗", None))[1])

    def _beta_command(self, q, ql):
        """Бета-функции: рабочее место, история копирования. None — это не про них."""
        if features.enabled("workspace", self.cfg):
            kind = workspace.command(ql)
            if kind:
                self._count_use("workspace")
            if kind == "save":
                apps = workspace.save(self.cfg, W.visible_apps())
                self.save_cfg()
                if not apps:
                    return Reply("Не вижу открытых программ, которые можно запомнить 🤔", "curious")
                return Reply(f"Запомнил рабочее место: {workspace.names(apps)} 🗂", None)
            if kind == "restore":
                if not workspace.saved_apps(self.cfg):
                    return Reply("Рабочее место ещё не запомнено. Открой нужные программы и скажи «запомни рабочее место».",
                                 "curious")
                todo = workspace.plan_restore(self.cfg, W.running_names())
                if not todo:
                    return Reply("Всё запомненное уже открыто 👍", None)
                return commands._ask(f"Открыть {len(todo)}: {workspace.names(todo)}?",
                                     lambda: self._open_workspace(todo))
        if features.enabled("clipboard_search", self.cfg):
            c = clipbuf.command(ql)
            if c:
                self._count_use("clipboard_search")
                if c[0] == "forget":
                    self.store.forget_clips()
                    return Reply("Историю копирования очистил 🧹", None)
                query = c[1].lower()
                hits = [(ts, t) for ts, t in self.store.list_clips() if not query or query in t.lower()][:5]
                if not hits:
                    return Reply("Ничего не нашёл в истории копирования 🤔" if query
                                 else "История копирования пока пуста.", "curious")
                fmt_ts = lambda ts: time.strftime("%d.%m %H:%M", time.localtime(ts))
                return Reply("Вот что нашёл:\n" + clipbuf.format_hits(hits, fmt_ts), None)
        more = self._beta_more(q, ql)
        if more:
            return more
        return None

    def _beta_more(self, q, ql):
        """Функции: здоровье ПК, очистка, порядок в загрузках, расписание."""
        if hogs.command(ql):
            return self._hogs_question()
        if errhelp.command(ql):
            return self._errhelp_question(errhelp.command(ql))
        if features.enabled("health", self.cfg) and health.command(ql):
            self._count_use("health")
            return Reply(health.report(W.disk_usage, W.boot_time(), time.time(), defender=W.defender_on()), None)
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
                    return Reply("Старых временных файлов нет — чистить нечего 👌", None)
                total = sum(s for _, s in files)
                return commands._ask(f"Отправить в корзину {len(files)} временных файлов старше суток ({cleanup._mb(total)})?",
                                     lambda: self._do_clean(files))
        if features.enabled("sorter", self.cfg):
            k = sorter.command(ql)
            if k == "sort":
                self._count_use("sorter")
                moves = sorter.plan(os.path.join(os.path.expanduser("~"), "Downloads"))
                if not moves:
                    return Reply("В «Загрузках» нечего раскладывать 👌", None)
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
                return Reply(f"Вернул на места файлов: {back} ↩", None)
        if features.enabled("schedule", self.cfg):
            low = ql.replace("ё", "е")
            if re.fullmatch(r"(покажи|какие\s+у\s+меня)\s+расписани\w*|мои\s+расписани\w*", low.strip(" .!?")):
                self._count_use("schedule")
                rules = self.cfg.get("schedules") or []
                return Reply("\n".join(f"• {r['action']} в {r['at']}" for r in rules) or "Расписаний нет.", None)
            if re.fullmatch(r"(удали|очисти)\s+(все\s+)?расписани\w*", low.strip(" .!?")):
                self.cfg["schedules"] = []
                self.save_cfg()
                return Reply("Расписания удалил 🧹", None)
            rules = schedule.parse(low, self._schedulable)
            if rules:
                self._count_use("schedule")
                self.cfg["schedules"] = (self.cfg.get("schedules") or []) + [
                    {"action": a, "at": at, "last": ""} for a, at in rules]
                self.save_cfg()
                text = "; ".join(f"«{a}» в {at}" for a, at in rules)
                return Reply(f"Запланировал: {text} ⏰", None)
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
        return Reply(f"Отправил в корзину {done} файлов (их можно вернуть из корзины), освободил {cleanup._mb(freed)}" +
                     (f", пропустил занятых: {skipped}" if skipped else "") + " 🧹", None)

    def _do_sort(self, moves):
        done, skipped = sorter.apply(moves)
        self.cfg["last_sort"] = [list(p) for p in done]
        self.save_cfg()
        return Reply(f"Разложил файлов: {len(done)}" + (f", пропустил занятых: {skipped}" if skipped else "")
                     + ". Чтобы вернуть, скажи «отмени сортировку» 📁", None)

    def _open_workspace(self, apps):
        opened = 0
        for a in apps:
            try:
                W.launch(a["exe"])
                opened += 1
            except OSError:
                pass
        return Reply(f"Открыл {opened} из {len(apps)} 🗂", None)

    def _clip_check(self, cc):
        """«Исправь текст из буфера»: берём буфер, отдаём модели на проверку орфографии."""
        clip = getattr(self, "clip_text", None)
        text = (clip() if clip else "") or ""
        text = text.strip()
        if not text:
            return Reply("В буфере пусто. Скопируй текст и повтори.", None)
        if clipbuf.looks_secret(text):
            return Reply("В буфере похоже на пароль или номер карты. Я его не трогаю.", None)
        try:
            out = self._chat(clipcheck.prompt(cc, text), self.cfg.get("text_model"))
        except Exception:
            return Reply("Не получилось проверить текст: модель не отвечает.", None)
        return Reply(out or "Ничего не получилось.", None)

    _SILENT_Q = re.compile(r"(почему|зачем|чего|что\s+с\s+тобой).*\b(не\s+отвеча\w*|молчишь|не\s+работа\w*|не\s+реагир\w*)"
                           r"|\bты\s+(не\s+отвеча\w*|молчишь|не\s+работа\w*)")

    def _why_silent(self, ql):
        """«Почему ты не отвечаешь?» — не отдаём общую справку, а проверяем Ollama и модель и говорим, что на самом деле."""
        if not self._SILENT_Q.search(ql):
            return None
        if BACKEND["name"] == "builtin":                       # встроенная модель: проверяем файл, без Ollama
            ok = bool(model_store.path_for(self.cfg.get("text_model") or "")) and \
                self.cfg.get("text_model") in model_store.installed_ids()
            if ok:
                return Reply("Я на связи: встроенная модель на месте. Спроси ещё раз. "
                             "Если снова молчу, скажи, что именно видишь: пустой ответ или ошибку.", "happy")
            return Reply("Встроенная модель не скачана. Скачай её в ⚙ Настройки → Модели.", "worried")
        import ollama_ctl
        if not ollama_ctl.is_running():
            threading.Thread(target=ollama_ctl.ensure_running, daemon=True).start()
            return Reply("Движок моделей сейчас не отвечает. Пытаюсь его запустить, это займёт несколько секунд. "
                         "Спроси ещё раз через полминуты.", "worried")
        model = self.cfg.get("text_model") or ""
        try:
            installed = list_models()
        except Exception:
            installed = []
        if model and not any(m == model or m.split(":")[0] == model.split(":")[0] for m in installed):
            return Reply(f"Движок работает, но модель «{model}» не найдена. Скачай её в ⚙ Настройки → Модели.", "worried")
        return Reply(f"Я на связи: движок работает, модель «{model}» на месте. Спроси ещё раз. "
                     "Если снова молчу, скажи, что именно видишь: пустой ответ или ошибку.", "happy")

    def _ask(self, q, rewritten=False):
        cc = clipcheck.command(q)
        if cc:
            return self._clip_check(cc)
        ql = q.lower()
        if self.cfg.get("memory_on", True) and q.strip() and not rewritten:      # учимся на том, что пользователь просит
            try:
                self.store.add_action(time.time(), q.strip())
            except Exception:
                pass
        refusal = guard.request_refusal(q)                       # запрещённое: не ищем и не отвечаем
        if refusal:
            return Reply(refusal, "curious")
        if phrase.is_greeting(q):                                # «доброе утро!», «привет 😊»
            return Reply(phrase.greeting_text(kind=phrase.greeting_kind(q)), None)
        status = self._why_silent(ql)                            # «почему ты не отвечаешь?» — проверяем на самом деле
        if status:
            return status
        remembered = self._recall(q)                             # «о чём мы говорили вчера»
        if remembered:
            return remembered
        refusal = smart.safety_refusal(ql)                       # опасное — не выполняем, объясняем
        if refusal:
            return Reply(refusal, "curious")
        calc = smart.calculate(q)                                # «сколько будет 17 умножить на 23»
        if calc:
            return Reply(calc, None)
        if smart.is_intro_question(ql):                          # «ты кто?»
            return Reply(smart.INTRO, None)
        if smart.is_toggle_question(ql):                         # «какие настройки ты умеешь переключать?»
            return Reply(smart.toggles_overview(components.TOGGLES), None)
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
        upd = self._manual_update(ql)                            # есть ли новая версия Mico AI?
        if upd:
            return upd
        beta = self._beta_command(q, ql)                         # бета: рабочее место, копирование
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
                return Reply(cap, None)
            if "буфер" in ql:
                return self._clipboard(ql)
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
                    return Reply(kb, None)
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
        except local_llm.LocalModelError as e:                 # встроенная модель: понятная причина, без падения
            return Reply(str(e), "sad")
