"""Голос Mico: Mico только слушает и ничего не говорит вслух.

Распознавание офлайн, через Vosk: модель лежит на этом ПК, ничего никуда не отправляется. Встроенные речевые
службы Windows (синтез и распознавание) не используются. Чистые функции здесь проверяются тестами без микрофона;
сам микрофон и модель проверяются на ПК (см. BETA_CHECKLIST)."""
import json
import os
import queue
import threading
import time

MIN_CONFIDENCE = 0.55                       # ниже — фраза слишком неясная, не выполняем
WAKE_MIN_CONFIDENCE = 0.35                  # одно слово «Мико» распознаётся неуверенно: для него порог ниже
CONVERSATION_SEC = 12                       # после слова «Мико» ещё столько секунд можно говорить без него

# Слово пробуждения и варианты, которые понимает распознаватель отдельным словом.
WAKE_WORDS = ("мико", "mico")                 # единственные слова пробуждения: настройку не меняем
# Как Vosk иногда слышит «Мико» в начале фразы. Принимаем их только внутри открытого окна разговора
# (после слова «Мико»), иначе обычные фразы вроде «никакой музыки» стали бы командами.
WAKE_MISHEARD = ("ником", "никакой", "никакого", "никакому", "никакое", "никакую", "никаким", "никакие",
                 "никаких", "никому")
QUESTION_WORDS = ("что", "как", "где", "когда", "почему", "зачем", "сколько", "какой", "какая", "какие",
                  "какое", "кто", "куда", "откуда", "можно ли", "ты ")


def normalize_dictation(text):
    """Аккуратная запись распознанной фразы: заглавная буква, знак в конце (вопрос или точка)."""
    t = " ".join(str(text or "").split())
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    if t[-1] not in ".!?…":
        low = t.lower()
        t += "?" if any(low.startswith(q + " ") or low == q for q in QUESTION_WORDS) else "."
    return t


def wake_words_from(setting):
    """Слова пробуждения: всегда «мико» и «mico»."""
    # Слова пробуждения фиксированы: «мико» и «mico». Настройка оставлена для совместимости и не используется.
    return tuple(WAKE_WORDS)


def _edit_distance(a, b):
    """Сколько букв надо поменять, добавить или убрать, чтобы из a получить b."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def is_wake_like(word, words=None):
    """Похоже ли слово на слово пробуждения, даже если Vosk его немного исказил («мигу» вместо «мико»).
    Совпадение по написанию: та же первая буква и отличие не больше двух букв (для коротких слов — одной).
    Используем только внутри открытого окна разговора, иначе обычные слова стали бы командами."""
    w = str(word or "").lower().strip(",.!?:;")
    if not w:
        return False
    if w in WAKE_MISHEARD:
        return True
    for target in (words or WAKE_WORDS):
        t = str(target).strip(" ,.!?:;").lower()
        if not t or w[0] != t[0] or abs(len(w) - len(t)) > 1:
            continue
        allowed = 2 if len(t) >= 4 else 1
        if _edit_distance(w, t) <= allowed:
            return True
    return False


def parse_wake(text, words=None, loose=False):
    """(True, команда), если фраза начинается со слова пробуждения; команда может быть пустой.
    loose=True — дополнительно принимаем искажённые варианты («ником», «мигу»)."""
    t = str(text or "").strip()
    head, _, rest = t.partition(" ")
    word = head.lower().strip(",.!?:;")
    accepted = set(words or WAKE_WORDS)
    if word in accepted or (loose and is_wake_like(word, words)):
        return True, rest.strip(" ,.!?:;")
    return False, ""


def strip_wake(text, words=None):
    """Текст для запроса без слова пробуждения. Если фраза начинается с него — возвращаем только команду.
    Так «Мико, открой макс» уходит в чат как «Открой макс», а не с «Мико» или «Ником» внутри."""
    wake, cmd = parse_wake(text, words, loose=True)
    return cmd if wake else str(text or "").strip()


def accept_phrase(text, confidence, minimum=MIN_CONFIDENCE):
    """Берём фразу только если распознавание уверено в ней достаточно и в ней есть что-то, кроме пустоты."""
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        conf = 0.0
    return conf >= minimum and len(str(text or "").split()) >= 1


class ConversationGate:
    """После слова «Мико» короткое окно: следующие фразы понимаем без него."""

    def __init__(self, window=CONVERSATION_SEC):
        self.window = window
        self._until = 0.0

    def open(self, now):
        self._until = now + self.window

    def is_open(self, now):
        return now < self._until


def wake_words_list(words=None):
    """Слова пробуждения без знаков препинания и повторов, по порядку."""
    out = []
    for w in (words or WAKE_WORDS):
        w = str(w).strip(" ,.!?:;").lower()
        if w and w not in out:
            out.append(w)
    return out


def _as_words(words):
    """Принимаем и строку из настроек («мико, микро»), и уже разобранный список/кортеж."""
    return wake_words_from(words) if isinstance(words, str) else words


def wake_grammar(words=None):
    """Короткий список слов для отдельного распознавателя «Мико»: сами слова пробуждения, их искажения
    (вроде «никакой», которое Vosk чаще всего выдаёт вместо «Мико») и [unk] для всего остального."""
    return json.dumps(wake_words_list(_as_words(words)) + list(WAKE_MISHEARD) + ["[unk]"], ensure_ascii=False)


def heard_wake(said, words=None):
    """Начинается ли услышанный кусок со слова пробуждения (или его искажения).
    Смотрим только на первое слово: «ну мико» или «я сказал никакой» — не обращение к Mico.
    Служебный [unk] пропускаем. Чистая функция, проверяется тестами без микрофона."""
    tokens = [t.strip(",.!?:;").lower() for t in str(said or "").split()]
    tokens = [t for t in tokens if t and t != "[unk]"]
    if not tokens:
        return False
    return tokens[0] in set(wake_words_list(_as_words(words))) | set(WAKE_MISHEARD)


def vosk_path(path):
    """Путь к модели, который Kaldi (Vosk) сможет открыть. На Windows он не понимает не-латинские буквы
    в пути (например, папка пользователя «Иван»): тогда берём короткое 8.3-имя папки. Если и его нет —
    путь как был. На не-Windows путь возвращается без изменений."""
    path = str(path or "")
    try:
        path.encode("ascii")
        return path
    except UnicodeEncodeError:
        pass
    if os.name == "nt":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(32768)
            n = ctypes.windll.kernel32.GetShortPathNameW(path, buf, 32768)
            if n and buf.value and buf.value.isascii():
                return buf.value
        except Exception:
            pass
    return path


_MODEL_CACHE = {}                           # путь → открытая модель Vosk (45 МБ — открываем один раз, а не на каждое нажатие 🎤)
_MODEL_LOCK = threading.Lock()


def load_model(model_dir):
    """Модель Vosk по папке. Открытая модель хранится и переиспользуется; другую папку — открываем заново."""
    import vosk
    path = vosk_path(model_dir)
    with _MODEL_LOCK:
        if path not in _MODEL_CACHE:
            _MODEL_CACHE.clear()
            _MODEL_CACHE[path] = vosk.Model(path)
        return _MODEL_CACHE[path]


def vosk_available():
    try:
        import vosk  # noqa: F401
        import sounddevice  # noqa: F401
        return True
    except Exception:
        return False


def vosk_problem(model_dir):
    """Почему Vosk сейчас не может слушать: текст для человека. Пусто — всё готово."""
    import voicemodel
    if not vosk_available():
        return ("Не открываются пакеты vosk и sounddevice. Проверь, что они установлены "
                "в том же Python, которым запускается Mico.")
    if not voicemodel.is_installed(model_dir or ""):
        return ("Модель распознавания не найдена. Укажи папку модели в ⚙ Настройки → Голос "
                "(в ней должны быть папки am и graph).")
    return ""


def decode_stream(chunks, recognizer, on_phrase):
    """Разбирает поток аудио-кусков: как только распознаватель закончил фразу, отдаём текст.
    Возвращает число отданных фраз. Чистая функция — проверяется тестами без микрофона."""
    count = 0
    for data in chunks:
        if recognizer.AcceptWaveform(data):
            text = (json.loads(recognizer.Result()).get("text") or "").strip()
            if text:
                on_phrase(text, 1.0)
                count += 1
    return count


def listen_once(cfg, timeout=8):
    """Одна фраза с микрофона через Vosk. Кнопка 🎤 в чате и в WI использует эту функцию.
    Возвращает (текст, ошибка)."""
    return listen_vosk((cfg or {}).get("vosk_model_dir") or "", timeout)


def listen_vosk(model_dir, timeout=8):
    """Одна фраза с микрофона через Vosk. Возвращает (текст, ошибка).
    Ошибки не глотаются: модель не открылась, микрофон занят — всё объясняется словами."""
    problem = vosk_problem(model_dir)
    if problem:
        return "", problem
    try:
        import sounddevice as sd
        import vosk
    except Exception as e:
        return "", f"Vosk не запустился: {e}"
    try:
        model = load_model(model_dir)
    except Exception as e:
        return "", f"Vosk не открыл модель ({e}). Проверь папку модели и попробуй перенести её в путь без русских букв."
    rec = vosk.KaldiRecognizer(model, 16000)
    q = queue.Queue()

    def cb(indata, frames, time_info, status):
        q.put(bytes(indata))
    deadline = time.time() + max(2, int(timeout))
    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=cb):
            while time.time() < deadline:
                try:
                    data = q.get(timeout=0.3)
                except queue.Empty:
                    continue
                if rec.AcceptWaveform(data):
                    text = (json.loads(rec.Result()).get("text") or "").strip()
                    if text:
                        return text, ""
            text = (json.loads(rec.FinalResult()).get("text") or "").strip()
            return text, ""
    except Exception as e:
        return "", f"Микрофон не открылся: {e}"


# ===================== постоянное прослушивание: «Мико, …» =====================
class VoskListener:
    """Фоновое прослушивание через Vosk: микрофон → модель на этом ПК.
    Каждая распознанная фраза уходит в on_phrase(text, confidence); слово пробуждения — в on_wake."""

    def __init__(self, model_dir, on_phrase, on_wake=None, wake_words=None, on_error=None, on_status=None):
        self.model_dir = model_dir
        self.on_status = on_status              # on_status(текст): «загружаю модель», «голос готов» — видно в чате
        self.on_phrase = on_phrase
        self.on_wake = on_wake                  # on_wake(confidence): слово пробуждения услышано отдельно
        self.wake_words = wake_words
        self.on_error = on_error                # on_error(текст): микрофон или модель отказали — скажем в чате
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        if self.listening():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_safe, daemon=True)
        self._thread.start()

    def _run_safe(self):
        """Поток не должен умирать молча: если микрофон или модель отказали, человек узнает причину."""
        try:
            self._run()
        except Exception as e:
            if self.on_error and not self._stop.is_set():
                self.on_error(f"Голос остановился: {e}. Открой ⚙ Настройки → Голос и нажми «Сохранить», чтобы запустить снова.")

    def _run(self):
        import sounddevice as sd
        q = queue.Queue()
        name = os.path.basename(os.path.normpath(self.model_dir or "")) or "Vosk"
        if self.on_status:
            self.on_status(f"Загружаю модель «{name}». Большие модели открываются до минуты — подожди, пожалуйста.")
        model = load_model(self.model_dir)
        import vosk
        rec = vosk.KaldiRecognizer(model, 16000)
        # Второй распознаватель — только для слова пробуждения: ему задан короткий список слов и их искажений.
        # Если модель таких слов не знает или распознаватель не создался — работает основной.
        words = wake_words_list(self.wake_words)
        rec_w = None
        if self.on_wake and words:
            try:
                rec_w = vosk.KaldiRecognizer(model, 16000, wake_grammar(self.wake_words))
            except Exception:
                rec_w = None

        def cb(indata, frames, time_info, status):
            q.put(bytes(indata))

        def chunks():
            while not self._stop.is_set():
                try:
                    yield q.get(timeout=0.5)
                except queue.Empty:
                    continue
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=cb):
            if self.on_status:
                self.on_status("Голос готов: слушаю. Скажи «мико» или «mico» и команду.")
            for data in chunks():
                if rec_w is not None and self._wake_heard(rec_w, data, words):
                    self.on_wake(1.0)
                if rec.AcceptWaveform(data):
                    text = (json.loads(rec.Result()).get("text") or "").strip()
                    if text:
                        self.on_phrase(text, 1.0)

    @staticmethod
    def _wake_heard(rec_w, data, words):
        """Слово пробуждения в этом куске звука (сразу, по частичному результату — не дожидаясь паузы)."""
        try:
            if rec_w.AcceptWaveform(data):
                said = json.loads(rec_w.Result()).get("text") or ""
            else:
                said = json.loads(rec_w.PartialResult()).get("partial") or ""
        except Exception:
            return False
        if heard_wake(said, words):
            rec_w.Reset()                       # одно слово — одно пробуждение
            return True
        return False

    def stop(self):
        self._stop.set()

    def listening(self):
        return self._thread is not None and self._thread.is_alive() and not self._stop.is_set()
