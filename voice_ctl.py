"""Голос Mico AI: озвучка ответов, голосовой ввод и пробуждение «мико». Один общий экземпляр на всё приложение
(чат, настройки и горячие клавиши работают с ним). Параметры берутся из настроек на каждой фразе — менять можно на лету.
Режимы микрофона: off — выключен; wake — ждём «мико!» (если включён голосовой запуск); cmd — записываем вопрос.
Звук нигде не сохраняется: фраза распознаётся и отбрасывается."""
import threading
import time

import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

import voice_log
import voice_models
import voice_text

MIC_RATE = 16000
MAX_LISTEN_SEC = 20
WAKE_END_SILENCE_MS = 600      # в режиме «мико» фраза короче: достаточно маленькой паузы
WAKE_MAX_SEC = 8

_SHARED = None


_MICS = None                      # список микрофонов, перечисленный в фоне: [(название, номер)]


def _enumerate_mics():
    global _MICS
    try:
        import sounddevice as sd                 # первый вызов загружает PortAudio — долго, поэтому не в окне настроек
        _MICS = [(d.get("name", f"Устройство {i}"), str(i))
                 for i, d in enumerate(sd.query_devices()) if d.get("max_input_channels", 0) > 0]
    except Exception:
        _MICS = []


def prefetch_mics():
    """Перечисляем микрофоны и загружаем PortAudio в фоновом потоке при старте, а не при открытии настроек."""
    threading.Thread(target=_enumerate_mics, daemon=True).start()


def mic_list():
    """Уже перечисленные микрофоны (пусто, пока фоновый поток не закончил). Окно настроек ничего не ждёт."""
    return list(_MICS or [])


def shared(cfg):
    """Единственный голосовой контроллер: чат, настройки и горячие клавиши используют один и тот же."""
    global _SHARED
    if _SHARED is None:
        _SHARED = VoiceCtl(cfg)
        prefetch_mics()
    return _SHARED


class VoiceCtl(QObject):
    said = pyqtSignal(str)        # распознанный вопрос: уходит как вопрос из чата
    speaking = pyqtSignal(bool)   # Mico говорит (рот и речь)
    sentence = pyqtSignal(str)    # фраза, которую Mico сейчас произносит (субтитры в голосовом режиме)
    level = pyqtSignal(float)     # громкость речи в этот момент (0..1)
    mic_level = pyqtSignal(float) # громкость микрофона: как громко говорит пользователь (0..1), для волн
    status = pyqtSignal(str)      # короткий статус для строки ввода; ошибки — в чат
    listening = pyqtSignal(bool)  # Mico слушает вопрос
    woke = pyqtSignal(str)        # услышали имя; текст после имени (может быть пустым)
    heard = pyqtSignal(str)       # что распознано в режиме «мико» (видно в строке ввода, чтобы понять, почему не реагирует)
    ready = pyqtSignal()          # модели загружены (или не загрузились — см. status)
    test_result = pyqtSignal(str) # итог проверки микрофона из настроек

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._tts = None
        self._stt = None
        self._loading = False
        self._gen = 0
        self._speaking = False
        self._stream = None
        self._lock = threading.Lock()
        self._new = []
        self._buf = []
        self._mode = "off"
        self._t_start = 0.0
        self._muted = False                 # микрофон выключен кнопкой в голосовом режиме
        self._session = False               # голосовой режим: отвечаем вслух, даже если озвучка выключена
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._tick)
        self.ready.connect(self._apply_mic)

    # ----- настройки (читаем на лету) -----
    def enabled(self):
        return bool(self.cfg.get("voice_on"))

    def wake_on(self):
        return bool(self.cfg.get("voice_wake"))

    def voice_name(self):
        name = self.cfg.get("voice_name") or voice_models.DEFAULT_VOICE
        return name if name in voice_models.VOICES else voice_models.DEFAULT_VOICE

    def _wake_words(self):
        return voice_text.wake_word_list(self.cfg.get("voice_wake_words", ""))

    def _end_ms(self):
        return int(max(400, min(3000, float(self.cfg.get("voice_end_ms", 1000)))))

    def _mic_device(self):
        raw = self.cfg.get("voice_mic", "")
        try:
            return int(raw) if str(raw).strip() != "" else None
        except (TypeError, ValueError):
            return None

    def set_enabled(self, on):
        self.cfg["voice_on"] = bool(on)
        if on:
            self.ensure_ready()
        else:
            self.stop_speaking()

    def set_voice(self, name):
        if name not in voice_models.VOICES:
            return
        self.cfg["voice_name"] = name
        if self.enabled() or self._session:
            self.ensure_ready()          # догрузит нужный движок; модель распознавания не трогаем

    def set_wake(self, on):
        self.cfg["voice_wake"] = bool(on)
        if on:
            self.status.emit("Жду «мико». Микрофон включён, звук не сохраняется.")
            self.ensure_ready()
        self._apply_mic()

    # ----- загрузка моделей (в фоне) -----
    def ensure_ready(self):
        if self._loading:
            return
        self._loading = True
        threading.Thread(target=self._prepare, daemon=True).start()

    def _prepare(self):
        self._attempt = self.voice_name()
        try:
            import sounddevice                   # прогреваем PortAudio здесь, в фоне, а не в первом касании микрофона
            name = self._attempt
            if not voice_models.is_installed(name):
                self.status.emit("Скачиваю голос (один раз, около 60 МБ)…")
                voice_models.download(name, progress=lambda f: self.status.emit(f"Скачиваю голос… {int(f * 100)}%"))
            self._tts = self._engine_for(name)
            self._voice_loaded = name
            if self._stt is None:
                self.status.emit("Загружаю распознавание речи…")
                from voice_stt import WhisperRu
                self._stt = WhisperRu()
            self.status.emit("")
        except Exception as e:
            self.status.emit(voice_log.record("Голос не запустился", e))
        finally:
            self._loading = False
            if self._attempt != self.voice_name() and self.enabled():
                self.ensure_ready()              # голос сменили во время загрузки — догружаем нужный (без цикла при ошибке)
            self.ready.emit()

    def _engine_for(self, name):
        """Движок под выбранный голос: Piper или RHVoice. Тот же голос не перезагружаем."""
        if voice_models.engine(name) == "rhvoice":
            from voice_tts import RHVoiceRu
            speaker = voice_models.VOICES[name]["speaker"]
            cur = self._tts
            if isinstance(cur, RHVoiceRu) and cur.speaker == speaker:
                return cur
            return RHVoiceRu(voice_models.rhvoice_exe(), speaker)
        from voice_tts import PiperRu
        model, conf = voice_models.paths(name)
        cur = self._tts
        if isinstance(cur, PiperRu) and cur.model_path == model:
            return cur
        return PiperRu(model, conf)

    # ----- озвучка -----
    def speak(self, text, mood="idle"):
        if not (self.enabled() or self._session):
            return
        sentences = voice_text.split_sentences(text)
        if not sentences:
            return
        self._gen += 1
        self._speaking = True
        threading.Thread(target=self._speak_worker, args=(sentences, self._gen, mood), daemon=True).start()

    def test_voice(self):
        """Кнопка «Проверить голос» в настройках: короткая фраза выбранным голосом и настроением."""
        self.speak("Привет! Так я звучу. Как тебе мой голос?", "happy")

    def set_session(self, on):
        """Голосовой режим: ответы говорим вслух, даже если «Озвучивать ответы» выключено. Настройку не трогаем.
        Пока голосовой режим открыт, ждать «мико!» не нужно: микрофон переходит к вопросам."""
        self._session = bool(on)
        if self._session and self._mode == "wake":
            self._close()
            self._mode = "off"
        self._apply_mic()                        # выход из голосового режима — «мико» снова слушаем сразу

    def arm_wake(self):
        """Снова слушаем «мико», если это включено и микрофон свободен. Вызываем после сна и пробуждения,
        чтобы слово работало и тогда, когда Mico спит."""
        self._apply_mic()

    def stop_speaking(self):
        self._gen += 1
        self._speaking = False
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        self.level.emit(0.0)
        self.speaking.emit(False)

    def _speak_worker(self, sentences, gen, mood):
        import sounddevice as sd
        self.speaking.emit(True)
        try:
            for sent in sentences:
                if gen != self._gen:
                    return
                tts = self._tts
                if tts is None:
                    self.ensure_ready()
                    return
                t = voice_text.tune(mood, self.cfg)
                audio, sr = tts.synth(sent, t)
                audio = audio * t["volume"]
                pause = voice_text.pause_after(sent) * t["pause"]
                audio = np.concatenate([audio, np.zeros(int(sr * pause), dtype=np.float32)])
                if gen != self._gen:
                    return
                env = voice_text.envelope(audio, sr)
                self.sentence.emit(sent)
                sd.play(audio, sr)
                t0 = time.time()
                dur = len(audio) / sr
                while gen == self._gen and time.time() - t0 < dur + 0.05:
                    self.level.emit(voice_text.level_at(env, time.time() - t0))
                    time.sleep(0.02)
                self.level.emit(0.0)
        except Exception as e:
            self.status.emit(voice_log.record("Голос не получился", e))
        finally:
            if gen == self._gen:
                self._speaking = False
                self.speaking.emit(False)

    # ----- микрофон -----
    def _open(self):
        if self._stream is not None:
            return True
        import sounddevice as sd
        try:
            self._stream = sd.InputStream(samplerate=MIC_RATE, channels=1, dtype="float32",
                                          device=self._mic_device(), callback=self._on_audio)
            self._stream.start()
            return True
        except Exception as e:
            self._stream = None
            self.status.emit(f"Микрофон не открылся: {e}")
            return False

    def _close(self):
        self._timer.stop()
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        self._mode = "off"
        with self._lock:
            self._new = []
        self._buf = []

    def _on_audio(self, indata, frames, t, status):
        with self._lock:
            self._new.append(indata[:, 0].copy())
        try:                                                # громкость блока — для волн в голосовом чате
            rms = float(np.sqrt(np.mean(np.square(indata[:, 0]))))
            self.mic_level.emit(min(1.0, rms * 9.0))
        except Exception:
            pass

    def _pull(self):
        with self._lock:
            self._buf.extend(self._new)
            self._new = []
        return np.concatenate(self._buf) if self._buf else np.zeros(0, dtype=np.float32)

    def _sens(self):
        return float(self.cfg.get("voice_wake_sens", 1.0))

    def _apply_mic(self):
        want = self._wake_active()
        if want and self._mode == "off":
            if self._open():
                self._mode = "wake"
                self._buf = []
                self._timer.start()
                self.status.emit("Жду «мико»")
        elif not want and self._mode == "wake":
            self._close()
            self.status.emit("")

    # ----- голосовой режим: микрофон открывают и закрывают кнопки из чата -----
    def muted(self):
        return self._muted

    def is_ready(self):
        return self._tts is not None and self._stt is not None

    def is_speaking(self):
        return self._speaking

    def set_muted(self, on):
        """Микрофон выключен: не слушаем ни вопрос, ни «мико». Фразу, которую записывали, отбрасываем."""
        self._muted = bool(on)
        if self._muted and self._mode == "cmd":
            self._stop_capture(recognize=False)
        self._apply_mic()
        if self._muted:
            self.status.emit("Микрофон выключен")

    def begin_listening(self):
        """Открыть микрофон и ждать вопрос. Ничего не делает, если микрофон выключен, Mico говорит,
        уже слушает или модель распознавания не загружена (загрузку здесь не запускаем повторно)."""
        if self._muted or self._mode == "cmd" or self._speaking or self._stt is None:
            return
        self._begin_command()

    def stop_listening(self):
        """Перестать слушать вопрос без отправки: Mico уже отвечает или выходим из голосового режима."""
        if self._mode == "cmd":
            self._stop_capture(recognize=False)

    def toggle_listen(self):
        """Горячая клавиша: начать запись, а если уже пишем — закончить и отправить."""
        if self._mode == "cmd":
            self._stop_capture(recognize=True)
        else:
            self._begin_command()

    def _wake_active(self):
        """Слушаем «мико!»: запуск включён, модель готова, микрофон не выключен и голосовой режим ещё не открыт."""
        return self.wake_on() and self._stt is not None and not self._muted and not self._session

    def _begin_command(self):
        if self._muted:
            self.status.emit("Микрофон выключен")
            return
        if self._stt is None:
            self.ensure_ready()
            self.status.emit("Голос ещё загружается, попробуй через минуту")
            return
        self.stop_speaking()
        if not self._open():
            return
        self._mode = "cmd"
        self._buf = []
        with self._lock:
            self._new = []
        self._t_start = time.time()
        self._timer.start()
        self.listening.emit(True)
        self.status.emit("Слушаю…")

    def _stop_capture(self, recognize):
        """Конец записи вопроса: возвращаемся к режиму «мико» (если он включён) или закрываем микрофон.
        recognize=False — фразу отбрасываем."""
        x = self._pull()
        self._buf = []
        self.listening.emit(False)
        if self._wake_active():
            self._mode = "wake"
            self.status.emit("Жду «мико»")
        else:
            self._close()
            self.status.emit("")
        if recognize:
            threading.Thread(target=self._recognize_cmd, args=(x,), daemon=True).start()

    def _tick(self):
        if self._stream is None:
            return
        if self._mode == "cmd":
            x = self._pull()
            thr = voice_text.adaptive_thresh(x, MIC_RATE, self._sens()) if len(x) else 0.012
            too_long = time.time() - self._t_start > MAX_LISTEN_SEC
            ended = voice_text.has_speech(x, MIC_RATE, thr) and \
                voice_text.trailing_silence_ms(x, MIC_RATE, thr) >= self._end_ms()
            if too_long or ended:
                self._stop_capture(recognize=True)
        elif self._mode == "wake":
            x = self._pull()
            if self._speaking:                       # Mico говорит — свой голос не слушаем
                self._buf = []
                return
            span = len(x) / MIC_RATE
            thr = voice_text.adaptive_thresh(x, MIC_RATE, self._sens()) if len(x) else 0.012
            speech = voice_text.has_speech(x, MIC_RATE, thr)
            if speech and (voice_text.trailing_silence_ms(x, MIC_RATE, thr) >= WAKE_END_SILENCE_MS or span >= WAKE_MAX_SEC):
                self._buf = []
                threading.Thread(target=self._recognize_wake, args=(x, thr), daemon=True).start()
            elif not speech and span > 3:
                self._buf = []

    # ----- распознавание (в фоне) -----
    def _recognize_wake(self, x, thr):
        if not voice_text.has_speech(x, MIC_RATE, thr):
            return
        try:
            text = self._stt.transcribe(x)
        except Exception:
            return
        self.heard.emit(text)
        rest = voice_text.after_wake(text, self._wake_words())
        if rest is not None:
            self.woke.emit(rest)


    def _recognize_cmd(self, x):
        thr = voice_text.adaptive_thresh(x, MIC_RATE, self._sens()) if len(x) else 0.012
        if not voice_text.has_speech(x, MIC_RATE, thr):
            self.status.emit("Не расслышал. Попробуй ещё раз.")
            return
        self.status.emit("Распознаю…")
        try:
            text = self._stt.transcribe(x)
        except Exception as e:
            self.status.emit(voice_log.record("Голос не распознал", e))
            return
        self.status.emit("")
        if text:
            self.said.emit(text)
        else:
            self.status.emit("Не разобрал слов. Попробуй ещё раз.")

    def test_mic(self, seconds=3.0):
        """Кнопка «Проверить микрофон»: записывает несколько секунд и показывает, что услышал Mico."""
        def work():
            try:
                import sounddevice as sd
                if self._stt is None:
                    self.test_result.emit("Модель распознавания ещё загружается, попробуй через минуту.")
                    return
                self.test_result.emit(f"Говори сейчас, {int(seconds)} с…")
                rec = sd.rec(int(seconds * MIC_RATE), samplerate=MIC_RATE, channels=1, dtype="float32",
                             device=self._mic_device())
                sd.wait()
                x = rec[:, 0]
                level = float(voice_text.frame_rms(x, MIC_RATE).max()) if len(x) else 0.0
                if not voice_text.has_speech(x, MIC_RATE, voice_text.adaptive_thresh(x, MIC_RATE, self._sens())):
                    self.test_result.emit(f"Речи не слышно (громкость {level:.3f}). Проверь микрофон и выбранное устройство.")
                    return
                text = self._stt.transcribe(x)
                self.test_result.emit(f"Услышал: «{text}»" if text else "Звук есть, но слов не разобрал.")
            except Exception as e:
                self.test_result.emit(f"Микрофон не проверился: {e}")
        threading.Thread(target=work, daemon=True).start()
