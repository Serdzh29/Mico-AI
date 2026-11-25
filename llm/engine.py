"""Встроенный движок: загружает GGUF-модель через llama-cpp-python прямо в Mico, без Ollama.
Библиотеку импортируем лениво: если её нет, Mico объясняет, как восстановить движок.
Модель держим в памяти, пока её используют, а через KEEP_SEC после последнего ответа выгружаем.
Где считать: на видеокарте NVIDIA, если она есть и сборка её умеет; иначе на процессоре — решает accel.py (см. prepare)."""
import gc
import importlib.util
import os
import re
import threading
import time

from llm import accel

KEEP_SEC = 120                              # после последнего ответа держим модель пару минут: частые вопросы не ждут загрузки
WATCH_SEC = 5                               # проверка простоя с небольшим интервалом
NO_THINK = " /no_think"                      # Qwen3-семейство: без рассуждений, сразу ответ (быстрее и без английского)
MAX_TOKENS = 1024                            # достаточно для полного ответа; не обрываем объяснения на полуслове
TEMPERATURE = 0.7                            # характер ответов по умолчанию; в настройках можно точнее/живее
CACHE_NAME = "llm_device.json"
CACHE_VERSION = "gpu2"                        # меняем, когда меняется логика выбора: старые записи не действуют
CTX = 4096                                # длинные диалоги помещаются целиком; под KV-кэш ужатая память (q8)
RU_RULE = "Всегда отвечай на русском языке, коротко и по делу."
RU_MARK = "Всегда отвечай на русском"


NO_ANSWER = "[thinking] Я задумался слишком долго и не успел ответить. Спроси ещё раз, покороче."
MOOD_TAGS = ("happy|love|sad|surprised|laugh|curious|worried|scared|angry|shy|confused|excited|proud|"
             "playful|thinking|sleepy|idle")
_REASONING_START = re.compile(r"^\s*(thinking( process)?|reasoning|analysis)\s*[:.\n]", re.I)
_ENGLISH_REASONING = re.compile(r"^\s*(the user|okay|ok,|let me|i need to|alright|hmm|so the|first,)", re.I)
_MOOD_LINE = re.compile(r"^[ \t]*(?:[*\-\u2022][ \t]*)?(\[(?:%s)\])[ \t]*(?=[\u0410-\u042f\u0430-\u044f\u0401\u0451])" % MOOD_TAGS,
                        re.M | re.I)


def _is_reasoning(text):
    return bool(_REASONING_START.match(text) or _ENGLISH_REASONING.match(text))


def _answer_in(text):
    """Ответ внутри рассуждения: последняя строка, где модель написала метку настроения и русский текст."""
    last = None
    for m in _MOOD_LINE.finditer(text):
        last = m
    return text[last.start(1):].strip() if last else ""


def clean_reply(text):
    """Убирает рассуждения модели. Шаблон Qwen сам ставит открывающий <think>, поэтому в ответе
    может быть только закрывающий </think> — всё до него тоже рассуждение. Если рассуждение обрезано
    лимитом и закрывающего тега нет, ответ ищем по метке настроения; если ответа нет — говорим честно."""
    text = str(text or "")
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    if "<think>" in text:                        # открыли, но не закрыли: всё после — рассуждение
        text = text.split("<think>", 1)[0]
    text = text.strip()
    if not text:
        return NO_ANSWER
    if _is_reasoning(text):                      # «Thinking Process: …» без тегов
        return _answer_in(text) or NO_ANSWER
    return text


_MOOD_HEAD = re.compile(r"^\[(?:%s)\]" % MOOD_TAGS, re.I)


class ReplyFilter:
    """Фильтр живого (потокового) ответа: по мере прихода текста убирает рассуждения и метку
    настроения, чтобы человек видел сразу чистый ответ. Начало немного держим, пока непонятно,
    метка это или текст. Финальная версия всё равно проходит clean_reply — здесь предпросмотр."""

    HOLD_TAG = 16                                # столько символов начала держим: метка не бывает длиннее

    def __init__(self):
        self._mode = "start"                     # start -> text / thinking / reasoning
        self._head = ""

    def feed(self, delta):
        """Кусочек модели -> кусочек чистого текста для показа (может быть пустым)."""
        self._head += str(delta or "")
        out = []
        while self._head:
            if self._mode == "thinking":                        # внутри рассуждения держим до закрытия
                if "</think>" in self._head:
                    self._head = self._head.split("</think>", 1)[1]
                    self._mode = "start"          # после рассуждения начало решаем заново: вдруг там метка
                else:
                    self._head = ""
            elif self._mode == "reasoning":                     # «Thinking Process: ...» без тегов
                m = _MOOD_LINE.search(self._head)               # ответ спрятан за меткой настроения
                if m:
                    self._head = self._head[m.end(1):]
                    self._mode = "text"
                else:
                    self._head = ""
            else:
                h = self._head.lstrip(" \n\t")
                if not h:
                    self._head = ""
                elif self._mode == "start" and "</think>" in h:
                    self._head = h.split("</think>", 1)[1]        # шаблон сам поставил закрывающий тег
                elif self._mode == "start" and _is_reasoning(h):
                    self._mode, self._head = "reasoning", ""
                elif "<think>" in h:
                    pre, _tail = h.split("<think>", 1)
                    self._mode = "thinking"
                    if pre.strip():
                        out.append(pre)
                    self._head = ""
                elif self._mode == "start" and h.startswith("["):
                    end = h.find("]")
                    if end < 0 and len(h) <= self.HOLD_TAG:
                        self._head = h            # подождём: возможно, это метка настроения
                        break
                    if 0 <= end <= self.HOLD_TAG and _MOOD_HEAD.match(h):
                        h = h[h.find("]") + 1:].lstrip(" ")   # метку убираем, текст показываем
                    self._mode, self._head = "text", ""
                    if h:
                        out.append(h)
                else:
                    self._mode, self._head = "text", ""
                    out.append(h)
        return "".join(out)


def _russian(messages):
    """Ответ всегда по-русски: правило добавляем в системное сообщение (один раз)."""
    out = [dict(m) for m in messages]
    for m in out:
        if m.get("role") == "system":
            if RU_MARK not in str(m.get("content", "")):
                m["content"] = str(m.get("content", "")) + "\n" + RU_RULE
            return out
    return [{"role": "system", "content": RU_RULE}] + out


def _messages_for(path, messages):
    """Русский всегда; рассуждения Qwen3 отключаем просьбой /no_think (Qwen2.5 её не знает и не нужна)."""
    out = _russian(messages)
    if "qwen3" in os.path.basename(path).lower():
        out = _no_think(out)
    return out


def _no_think(messages):
    """Копия переписки, где последнее сообщение пользователя просит без рассуждений."""
    out = [dict(m) for m in messages]
    for m in reversed(out):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            if not m["content"].rstrip().endswith("/no_think"):
                m["content"] = m["content"] + NO_THINK
            break
    return out


class LocalModelError(RuntimeError):
    pass


_GRAMMARS = {}


def _grammar(schema):
    """Грамматика llama.cpp по JSON-схеме: модель физически не может выдать битый JSON.
    None — сборка без грамматик: остаётся обычный повтор с проверкой."""
    if schema in _GRAMMARS:
        return _GRAMMARS[schema]
    g = None
    try:
        from llama_cpp import LlamaGrammar
        g = LlamaGrammar.from_json_schema(schema, verbose=False)
    except Exception:
        g = None
    _GRAMMARS[schema] = g
    return g


def available():
    """Установлена ли библиотека llama-cpp-python (без её импорта)."""
    return importlib.util.find_spec("llama_cpp") is not None


def gpu_supported():
    """Умеет ли эта сборка llama-cpp-python работать с видеокартой (CUDA/Vulkan)."""
    try:
        import llama_cpp
        return bool(llama_cpp.llama_supports_gpu_offload())
    except Exception:
        return False


def _cache_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Mico", CACHE_NAME)


def _threads():
    """Оставляем процессору ресурсы для Windows и интерфейса Mico во время генерации."""
    try:
        import psutil
        n = psutil.cpu_count(logical=False)
    except Exception:
        n = None
    cores = n or max(2, (os.cpu_count() or 4) // 2)
    return max(1, min(4, cores // 2 or 1))


class _Engine:
    def __init__(self):
        self._lock = threading.Lock()
        self._llm = None
        self._path = None
        self._layers = None
        self._last = 0.0
        self._watching = False

    def _load(self, path, layers):
        from llama_cpp import Llama
        threads = _threads()
        base = dict(model_path=path, n_ctx=CTX, n_threads=threads, n_threads_batch=threads,
                    n_batch=64, n_ubatch=64, n_gpu_layers=layers, verbose=False)
        try:                                   # ужатая память под историю (q8) и быстрое внимание, если сборка умеет
            return Llama(**base, flash_attn=True, type_k=8, type_v=8)
        except TypeError:
            return Llama(**base)


    def _ensure_locked(self, path):
        """Модель загружена и готова (вызывается под self._lock). Возвращает текст ошибки или None."""
        if not available():
            return ("Встроенная модель недоступна: не установлена библиотека llama-cpp-python. "
                    "Переустанови Mico AI, чтобы восстановить локальную модель.")
        if path not in _DEVICE:                 # первый раз: проверяем видеокарту до ответа (один раз на модель)
            prepare(path)
        layers = _DEVICE.get(path, (accel.CPU, ""))[0]
        if self._llm is None or self._path != path or self._layers != layers:
            self._unload_locked()
            try:
                self._llm = self._load(path, layers)
            except Exception as e:
                if layers == accel.CPU:
                    return f"Не получилось загрузить модель: {e}"
                # видеокарта не справилась при загрузке - переходим на процессор и запоминаем это
                _DEVICE[path] = (accel.CPU, "видеокарта не справилась с моделью, отвечаю на процессоре")
                layers = accel.CPU
                try:
                    self._llm = self._load(path, layers)
                except Exception as e2:
                    return f"Не получилось загрузить модель: {e2}"
            self._path = path
            self._layers = layers
            self._last = time.time()                 # загрузили - отсчёт простоя начинается сейчас
            self._start_watch()
        return None

    def chat(self, path, messages, max_tokens=700, temperature=None, json_schema=None):
        with self._lock:
            err = self._ensure_locked(path)
            if err:
                raise LocalModelError(err)
            gram = _grammar(json_schema) if json_schema else None
            out = self._llm.create_chat_completion(messages=_messages_for(path, messages),
                                                   max_tokens=min(max_tokens, MAX_TOKENS),
                                                   temperature=TEMPERATURE if temperature is None else temperature,
                                                   **({"grammar": gram} if gram else {}))
            self._last = time.time()
            return clean_reply(out["choices"][0]["message"]["content"])

    def chat_stream(self, path, messages, max_tokens=700, on_delta=None, temperature=None, json_schema=None):
        """Живой ответ: текст отдаётся кусочками по мере генерации, не дожидаясь конца.
        on_delta получает уже чистые кусочки - без рассуждений и метки настроения."""
        with self._lock:
            err = self._ensure_locked(path)
            if err:
                raise LocalModelError(err)
            gram = _grammar(json_schema) if json_schema else None
            out = self._llm.create_chat_completion(messages=_messages_for(path, messages),
                                                   max_tokens=min(max_tokens, MAX_TOKENS),
                                                   temperature=TEMPERATURE if temperature is None else temperature,
                                                   stream=True,
                                                   **({"grammar": gram} if gram else {}))
            flt = ReplyFilter()
            raw = []
            for chunk in out:
                delta = (chunk.get("choices") or [{}])[0].get("delta", {}).get("content") or ""
                if not delta:
                    continue
                raw.append(delta)
                if on_delta is not None:
                    shown = flt.feed(delta)
                    if shown:
                        try:
                            on_delta(shown)
                        except Exception:
                            pass                     # живой предпросмотр не должен ронять генерацию
            self._last = time.time()
            return clean_reply("".join(raw))

    def _unload_locked(self):
        self._llm = None
        self._path = None
        self._layers = None
        gc.collect()

    def unload_if_idle(self):
        with self._lock:
            if self._llm is not None and time.time() - self._last > KEEP_SEC:
                self._unload_locked()

    def _start_watch(self):
        """Фоновая проверка простоя. Раньше unload_if_idle() никто не вызывал, и встроенная модель
        оставалась в памяти до закрытия Mico AI. Поток запускается при первой загрузке модели."""
        if self._watching:
            return
        self._watching = True

        def loop():
            while True:
                time.sleep(WATCH_SEC)
                try:
                    self.unload_if_idle()
                except Exception:
                    pass                                 # выгрузка не должна ронять приложение
        threading.Thread(target=loop, daemon=True, name="llm-idle-watch").start()

    def _try_load(self, path, layers):
        """Проверка: модель загружается на этих слоях и отвечает хотя бы одним токеном. True — можно работать."""
        try:
            llm = self._load(path, layers)
        except Exception:
            return False
        try:
            llm.create_chat_completion(messages=_messages_for(path, [{"role": "user", "content": "Привет"}]),
                                       max_tokens=1, temperature=0.0)
            return True
        except Exception:
            return False
        finally:
            del llm
            gc.collect()


_ENGINE = _Engine()
_DEVICE = {}                                   # путь к модели → (слои на видеокарте, отчёт для пользователя)
_PREPARING = set()


def prepare(path):
    """Проверяет, где быстрее: видеокарта или процессор. Результат запоминается на диске.
    Занимает несколько секунд (пробная загрузка), результат сохраняется; повторно не проверяем. Возвращает отчёт или None."""
    if not available() or not os.path.isfile(path):
        return None
    with _ENGINE._lock:
        if path in _DEVICE:
            return _DEVICE[path][1]
        _ENGINE._unload_locked()
        info = accel.gpu_info()
        model_mb = os.path.getsize(path) / (1024 ** 2)
        cache_file = _cache_path()
        cache = accel.load_cache(cache_file)
        key = f"{CACHE_VERSION}|{os.path.basename(path)}|{info['name'] if info else 'нет'}"
        layers, report = accel.choose(model_mb, info, gpu_supported(),
                                      lambda n: _ENGINE._try_load(path, n), cache, key)
        accel.save_cache(cache_file, cache)
        _DEVICE[path] = (layers, report)
        return report


def prepare_async(path):
    """То же, что prepare, но в фоновом потоке: окно и ответы не ждут."""
    if path in _PREPARING or path in _DEVICE:
        return
    _PREPARING.add(path)

    def run():
        try:
            prepare(path)
        finally:
            _PREPARING.discard(path)
    threading.Thread(target=run, daemon=True).start()


def chat(path, messages, max_tokens=700, temperature=None, json_schema=None):
    return _ENGINE.chat(path, messages, max_tokens, temperature, json_schema)


def chat_stream(path, messages, max_tokens=700, on_delta=None, temperature=None, json_schema=None):
    return _ENGINE.chat_stream(path, messages, max_tokens, on_delta, temperature, json_schema)


WARM_SEC = 180                             # повторная прогревка - не чаще, чем раз в три минуты
_WARMED = {}


def warmup(path):
    """Фоновая прогревка: модель загружается заранее, чтобы первый вопрос не ждал загрузки.
    Запускается при старте и при открытии чата; ошибки прогрева никто не видит - это удобство."""
    if not available() or not os.path.isfile(path):
        return
    now = time.time()
    if now - _WARMED.get(path, 0) < WARM_SEC:
        return
    _WARMED[path] = now

    def run():
        try:
            prepare(path)                       # проверка видеокарты - тоже заранее
            _ENGINE.chat(path, [{"role": "user", "content": "\u041f\u0440\u0438\u0432\u0435\u0442"}], max_tokens=8)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True, name="llm-warmup").start()


def unload_if_idle():
    _ENGINE.unload_if_idle()
