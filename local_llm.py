"""Встроенный движок: загружает GGUF-модель через llama-cpp-python прямо в Mico, без Ollama.
Библиотеку импортируем лениво: если её нет, Mico работает через Ollama, как раньше.
Модель держим в памяти, пока её используют, а через KEEP_SEC после последнего ответа выгружаем.
Где считать: на видеокарте NVIDIA, если она есть и сборка её умеет; иначе на процессоре — решает accel.py (см. prepare)."""
import gc
import importlib.util
import os
import re
import threading
import time

import accel

KEEP_SEC = 120                             # через 2 минуты без ответов модель уходит из памяти
NO_THINK = " /no_think"                      # Qwen3-семейство: без рассуждений, сразу ответ (быстрее и без английского)
MAX_TOKENS = 320                             # короткий ответ в чате: быстрее и без лишней работы
CACHE_NAME = "llm_device.json"
CACHE_VERSION = "gpu2"                        # меняем, когда меняется логика выбора: старые записи не действуют
CTX = 2048                                # контекст: меньше памяти под историю диалога
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
    """Потоки по физическим ядрам: так быстрее, чем по всем логическим."""
    try:
        import psutil
        n = psutil.cpu_count(logical=False)
    except Exception:
        n = None
    return max(2, n or (os.cpu_count() or 4) // 2)


class _Engine:
    def __init__(self):
        self._lock = threading.Lock()
        self._llm = None
        self._path = None
        self._layers = None
        self._last = 0.0

    def _load(self, path, layers):
        from llama_cpp import Llama
        threads = _threads()
        base = dict(model_path=path, n_ctx=CTX, n_threads=threads, n_gpu_layers=layers, verbose=False)
        try:                                   # ужатая память под историю (q8) и быстрое внимание, если сборка умеет
            return Llama(**base, flash_attn=True, type_k=8, type_v=8)
        except TypeError:
            return Llama(**base)


    def chat(self, path, messages, max_tokens=700):
        if not available():
            raise LocalModelError("Встроенная модель недоступна: не установлена библиотека llama-cpp-python. "
                                  "Выбери другую модель в ⚙ Настройки → Модели.")
        if path not in _DEVICE:                 # первый раз: проверяем видеокарту до ответа (один раз на модель)
            prepare(path)
        with self._lock:
            layers = _DEVICE.get(path, (accel.CPU, ""))[0]
            if self._llm is None or self._path != path or self._layers != layers:
                self._unload_locked()
                try:
                    self._llm = self._load(path, layers)
                except Exception as e:
                    if layers == accel.CPU:
                        raise LocalModelError(f"Не получилось загрузить модель: {e}")
                    # видеокарта не справилась при загрузке — переходим на процессор и запоминаем это
                    _DEVICE[path] = (accel.CPU, "видеокарта не справилась с моделью, отвечаю на процессоре")
                    layers = accel.CPU
                    try:
                        self._llm = self._load(path, layers)
                    except Exception as e2:
                        raise LocalModelError(f"Не получилось загрузить модель: {e2}")
                self._path = path
                self._layers = layers
            out = self._llm.create_chat_completion(messages=_messages_for(path, messages),
                                                   max_tokens=min(max_tokens, MAX_TOKENS), temperature=0.7)
            self._last = time.time()
            return clean_reply(out["choices"][0]["message"]["content"])

    def _unload_locked(self):
        self._llm = None
        self._path = None
        self._layers = None
        gc.collect()

    def unload_if_idle(self):
        with self._lock:
            if self._llm is not None and time.time() - self._last > KEEP_SEC:
                self._unload_locked()

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


def device_report(path):
    """Что решила проверка для этой модели — для настроек и журнала. None — ещё не проверяли."""
    hit = _DEVICE.get(path)
    return hit[1] if hit else None


def chat(path, messages, max_tokens=700):
    return _ENGINE.chat(path, messages, max_tokens)


_VISION_LOCK = threading.Lock()


def describe_image(model_path, mmproj_path, prompt, image_b64, max_tokens=300):
    """Ответ модели для экрана: картинка (base64 PNG) + вопрос. Модель загружается на время ответа и выгружается.
    Считается на видеокарте, если она есть (как и текст); если не получилось — на процессоре.
    Нужна сборка llama-cpp-python с поддержкой Qwen2.5-VL (обработчик картинки). Без неё — LocalModelError."""
    if not available():
        raise LocalModelError("Встроенная модель недоступна: не установлена библиотека llama-cpp-python.")
    try:
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Qwen25VLChatHandler
    except Exception:
        raise LocalModelError("Эта сборка движка не умеет смотреть на экран. Выбери другую модель в ⚙ Настройки → Модели.")
    if model_path not in _DEVICE:
        prepare(model_path)
    gpu_layers = _DEVICE.get(model_path, (accel.CPU, ""))[0]
    with _VISION_LOCK:
        try:
            handler = Qwen25VLChatHandler(clip_model_path=mmproj_path, verbose=False)
        except Exception as e:
            raise LocalModelError(f"Не получилось загрузить модель для экрана: {e}")
        llm, err = None, None
        for layers in dict.fromkeys([gpu_layers, accel.CPU]):      # сначала видеокарта, потом процессор
            try:
                llm = Llama(model_path=model_path, chat_handler=handler, n_ctx=4096,
                            n_gpu_layers=layers, verbose=False)
                break
            except Exception as e:
                err = e
        if llm is None:
            raise LocalModelError(f"Не получилось загрузить модель для экрана: {err}")
        try:
            content = [{"type": "text", "text": prompt},
                       {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image_b64}}]
            out = llm.create_chat_completion(messages=[{"role": "user", "content": content}],
                                             max_tokens=min(max_tokens, MAX_TOKENS), temperature=0.3)
            return clean_reply(out["choices"][0]["message"]["content"])
        finally:
            del llm
            gc.collect()


def unload_if_idle():
    _ENGINE.unload_if_idle()
