"""Голос Mico AI без Qt, микрофона и динамиков: чистая логика, модели (хеши, докачка), id фонем, рот по громкости."""
import os as _os, sys, re, tempfile, time, urllib.request, io
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
exec(open(_os.path.join(ROOT, "tests", "test_animations.py"), encoding="utf-8").read().split("import blob as Bl")[0])
import numpy as np
import blob as Bl
import voice_text as VT
import voice_models as VM

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

# ---------- текст для речи ----------
def test_clean_removes_tags_links_code_emoji_markup():
    s = VT.clean_for_speech("[happy] **Привет!** 😊 Смотри https://ex.ru и `x = 1`\n```py\nprint(1)\n```\n# Заголовок")
    check("[" not in s and "http" not in s and "*" not in s and "`" not in s and "print" not in s, s)
    check("Привет!" in s and "Заголовок" in s and "😊" not in s, s)

def test_split_sentences_by_end_marks_and_length():
    parts = VT.split_sentences("Первое предложение. Второе! Третье?\nЧетвёртое")
    check(parts == ["Первое предложение.", "Второе!", "Третье?", "Четвёртое"], parts)
    long = " ".join(["слово"] * 80)
    chunks = VT.split_sentences(long, max_len=120)
    check(len(chunks) > 1 and all(len(c) <= 120 for c in chunks), chunks)
    check(VT.split_sentences("   ") == [], "пустой текст")

# ---------- громкость для рта ----------
def test_envelope_follows_loudness_over_time():
    sr = 22050
    t = np.arange(sr) / sr
    loud = 0.5 * np.sin(2 * np.pi * 200 * t)
    loud[: sr // 2] *= 0.05                              # первая половина тихая, вторая громкая
    env = VT.envelope(loud, sr)
    check(len(env) > 40 and env.max() <= 1.0 and env.min() >= 0.0)
    check(env[: len(env) // 4].mean() < env[3 * len(env) // 4:].mean(), "громкость не повторяет звук")
    check(VT.level_at(env, 0.9) > 0.8 and VT.level_at(env, 0.1) < 0.2, (VT.level_at(env, 0.1), VT.level_at(env, 0.9)))
    check(VT.level_at(None, 1.0) == 0.0 and VT.level_at(env, -1) == 0.0 and VT.level_at(env, 99) <= 1.0)

def test_mouth_opens_with_level_and_stays_bounded():
    lo, hi = VT.mouth_for_level(0.0), VT.mouth_for_level(1.0)
    check(lo[1] < 0.03 and hi[1] > 0.12, (lo, hi))
    mids = [VT.mouth_for_level(x / 10)[1] for x in range(11)]
    check(all(a <= b for a, b in zip(mids, mids[1:])), "рот должен открываться монотонно")
    check(VT.mouth_for_level(-5) == VT.mouth_for_level(0) and VT.mouth_for_level(9) == VT.mouth_for_level(1))

# ---------- конец речи пользователя ----------
def test_silence_and_speech_detection():
    sr = 16000
    speech = 0.3 * np.sin(2 * np.pi * 220 * np.arange(sr) / sr)
    quiet = np.zeros(sr, dtype=np.float32)
    check(VT.has_speech(speech, sr) and not VT.has_speech(quiet, sr), "речь не отличили от тишины")
    check(not VT.has_speech(speech[: sr // 10], sr), "короткий щелчок — не речь")
    rec = np.concatenate([speech, np.zeros(int(sr * 1.5), dtype=np.float32)])   # полторы секунды тишины
    ms = VT.trailing_silence_ms(rec, sr)
    check(1400 <= ms <= 1600, ms)
    check(VT.trailing_silence_ms(speech, sr) == 0, "тишины в конце нет")

# ---------- модели ----------
def test_voice_manifest_is_well_formed():
    """Четыре голоса Piper (с файлом и sha256) и четыре голоса RHVoice (с именем диктора, без скачивания)."""
    piper = {k for k, v in VM.VOICES.items() if v["engine"] == "piper"}
    rhv = {k for k, v in VM.VOICES.items() if v["engine"] == "rhvoice"}
    check(piper == {"irina", "dmitri", "denis", "ruslan"}, piper)
    check(rhv == {"rv_aleksandr", "rv_anna", "rv_elena", "rv_irina"}, rhv)
    check(set(VM.VOICES) == piper | rhv, "других движков в каталоге нет")
    for name in piper:
        v = VM.VOICES[name]
        check(v["file"] == f"ru_RU-{name}-medium.onnx", v["file"])
        check(re.fullmatch(r"[0-9a-f]{64}", v["sha256"]), (name, v["sha256"]))
    for name in rhv:
        v = VM.VOICES[name]
        check(v.get("speaker") and "file" not in v and "sha256" not in v, (name, v))
    titles = [v["title"] for v in VM.VOICES.values()]
    check(len(titles) == len(set(titles)), "названия голосов уникальны")
    check(VM.DEFAULT_VOICE in VM.VOICES and VM.engine(VM.DEFAULT_VOICE) == "piper")
    check(VM.RHVOICE_SITE == "https://rhvoice.org", "ссылка на RHVoice — официальная")
    check("scipy" in open(_os.path.join(ROOT, "requirements.txt"), encoding="utf-8").read(), "scipy в зависимостях")
    model, conf = VM.paths("irina")
    check(model.endswith("ru_RU-irina-medium.onnx") and conf == model + ".json", (model, conf))
    for f in ["voice_models.py", "voice_tts.py", "voice_ctl.py", "voice_settings.py", "voice_text.py"]:
        check(not re.search(r"silero|vosk", open(_os.path.join(ROOT, f), encoding="utf-8").read(), re.I), f)

def test_hashes_match_uploaded_models_when_present():
    """Если файлы голосов лежат рядом (как в загрузке), их хеши должны совпадать с манифестом."""
    folder = "/mnt/user-data/uploads"
    if not _os.path.isdir(folder):
        return
    for name, v in VM.VOICES.items():
        if v["engine"] != "piper":
            continue
        p = _os.path.join(folder, v["file"])
        if _os.path.isfile(p):
            check(VM.sha256_file(p) == v["sha256"], f"хеш не совпал: {name}")

def test_missing_voice_is_not_installed_and_download_checks_hash():
    real_dir = VM.VOICES_DIR
    with tempfile.TemporaryDirectory() as tmp:
        VM.VOICES_DIR = tmp
        try:
            check(not VM.is_installed("irina"), "пустая папка — голос не установлен")
            real_open = urllib.request.urlopen

            class _Resp(io.BytesIO):
                headers = {"Content-Length": "5"}
                def __enter__(self): return self
                def __exit__(self, *a): return False

            urllib.request.urlopen = lambda url, timeout=0: _Resp(b"fake!")   # неверные данные
            try:
                VM.download("irina")
                raise AssertionError("битый файл должен быть отвергнут")
            except ValueError as e:
                check("контрольная сумма" in str(e), e)
            finally:
                urllib.request.urlopen = real_open
            onnx, _ = VM.paths("irina")
            check(not _os.path.exists(onnx) and not _os.path.exists(onnx + ".part"), "битый файл не должен остаться")
            check(not VM.is_installed("irina"))
        finally:
            VM.VOICES_DIR = real_dir

# ---------- синтез через публичный API piper-tts ----------
def test_piper_uses_public_api_and_build_collects_voice_packages():
    src = open(_os.path.join(ROOT, "voice_tts.py"), encoding="utf-8").read()
    check("from piper import PiperVoice" in src and "piper_phonemize" not in src and "phonemize_espeak" not in src,
          "синтез должен идти через PiperVoice, без внутренних модулей фонемизации")
    for f in ["build_exe.bat", ".github/workflows/release.yml"]:
        b = open(_os.path.join(ROOT, f), encoding="utf-8").read()
        check("download.pytorch.org" not in b and "vosk-tts" not in b, f"{f}: PyTorch и vosk-tts не ставим")
        for pkg in ["faster_whisper", "piper", "piper_phonemize", "onnxruntime", "scipy"]:
            check(f"--collect-all {pkg}" in b, f"{f}: нет --collect-all {pkg} (нужны данные для exe)")

# ---------- рот в Blob по настоящей речи ----------
def make_blob():
    b = Bl.Blob.__new__(Bl.Blob)
    b.anim, b.talking, b.asleep, b.typing_until = None, False, False, 0
    b.squash = b.squash_v = 0.0
    b.start_anim = lambda name: setattr(b, "anim", (name, 0, 1))
    return b

def run(b, t, seconds):
    for _ in range(int(seconds * 60)):
        t += 1 / 60
        Bl.Blob._life(b, t, 1 / 60)
    return t

def test_blob_mouth_follows_voice_level():
    b = make_blob()
    t = run(b, 500.0, 0.0)
    b.set_speaking(True)
    b.set_voice_level(1.0)
    t = run(b, t, 0.8)
    want = VT.mouth_for_level(1.0)[1]
    check(abs(b.mh - want) < 0.02, (b.mh, want))
    b.set_voice_level(0.0)
    t = run(b, t, 0.8)
    check(b.mh < 0.03, b.mh)
    b.set_speaking(False)
    check(b.voice_level is None and not b.talking and not b.voice_active, "после речи рот отпускает")

def test_voice_speaking_survives_text_timer():
    """Таймер текстового ответа не должен закрывать рот, пока говорит настоящий голос."""
    src = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    i = src.index("def _stop_talk(self):")
    check("if not self.blob.voice_active" in src[i:i + 200], "_stop_talk должен учитывать голос")

# ---------- подключение ----------
def test_voice_is_wired_into_chat_and_answers():
    iu = open(_os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    for must in ["self.voice.said.connect(self._on_voice_said)", "self.voice.speaking.connect(self.blob.set_speaking)",
                 "self.voice.level.connect(self.blob.set_voice_level)", "self.aichat.listen.connect(self.enter_voice_mode)",
                 "self.voice.speak(text, mood)"]:
        check(must in iu, must)
    main = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    check("4: cfg.get(\"hotkey_voice\"" in main and "hid == 4" in main, "горячая клавиша голоса")
    check("\"voice_on\": False" in main and "\"hotkey_voice\"" in main, "настройки по умолчанию")

def test_voice_default_off_and_no_forbidden_engines():
    main = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    check("\"voice_on\": False" in main, "голос выключен по умолчанию")
    for f in ["voice_ctl.py", "voice_tts.py", "voice_stt.py", "voice_models.py", "voice_text.py"]:
        src = open(_os.path.join(ROOT, f), encoding="utf-8").read()
        check(not re.search(r"pyttsx3|SAPI|SpeechSynthesizer|speech_recognition|recognize_google", src), f)

# ---------- выразительность и пробуждение «мико» ----------
def test_every_mood_has_prosody_and_pause_is_sane():
    import emotions
    for m in emotions.VALID:
        length, noise, noise_w = VT.prosody(m)
        check(0.8 <= length <= 1.3 and 0.4 <= noise <= 1.0 and 0.4 <= noise_w <= 1.2, (m, length, noise, noise_w))
    check(VT.prosody("unknown") == VT.PROSODY["idle"], "неизвестное настроение — обычный голос")
    check(VT.pause_after("Да...") > VT.pause_after("Да.") > VT.pause_after("Да") > 0, "паузы по знакам")
    check(VT.pause_after("Точно?") == 0.35 and VT.pause_after("Ура!") == 0.3)

def test_faster_moods_are_faster_and_sad_is_slower():
    check(VT.prosody("excited")[0] < VT.prosody("idle")[0] < VT.prosody("sad")[0], "скорость по настроению")

def test_wake_word_matches_whole_words_only_at_start():
    check(VT.after_wake("Мико, какая погода?") == "какая погода", VT.after_wake("Мико, какая погода?"))
    check(VT.after_wake("Mico!") == "", "просто имя — пустой остаток")
    check(VT.after_wake("привет, мико") == "", "имя в начале фразы: сюда не выходит за 6 слов")
    check(VT.after_wake("микрофон включи") is None, "«микрофон» — не «мико»")
    check(VT.after_wake("мико тут") == "тут")
    check(VT.after_wake("") is None and VT.after_wake(None) is None)
    late = "один два три четыре пять шесть семь мико"
    check(VT.after_wake(late) is None, "имя далеко в середине фразы не будит")

def test_listening_pose_opens_eyes_and_tilts_head():
    b = make_blob()
    b.typing_until = 0
    t = run(b, 800.0, 0.6)
    base_eye, base_tilt = b.eye_k, b.tilt
    b.set_listening(True)
    t = run(b, t, 1.0)
    check(b.eye_k > base_eye + 0.05 and b.eye_k < 1.2, (base_eye, b.eye_k))
    b.set_listening(False)
    check(b.listen_voice is False)

def test_voice_never_writes_audio_to_disk():
    src = open(_os.path.join(ROOT, "voice_ctl.py"), encoding="utf-8").read()
    check("'wb'" not in src and '"wb"' not in src and "np.save" not in src and "wave.open" not in src,
          "голос не должен сохранять звук на диск")

def test_wake_and_mood_are_wired():
    iu = open(_os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
    for must in ["self.voice.woke.connect(self._on_wake)",
                 "self.blob.set_listening(on)", "emotions.split_mood(text)", "emotions.detect_emotion(text)",
                 "self.voice.speak(text, mood)"]:
        check(must in iu, must)
    wc = open(_os.path.join(ROOT, "aichat.py"), encoding="utf-8").read()
    check("Слушать «мико»" not in wc and "wake_toggle" not in wc, "«Слушать мико» нигде не предлагаем")
    main = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    check("\"voice_wake\": False" in main, "слушание «мико» выключено по умолчанию")

# ---------- микрофон: тихий и шумный режим; слова пробуждения; настройки ----------
def test_adaptive_threshold_hears_quiet_speech_over_background():
    """Раньше порог был фиксированным (0.012): тихий микрофон никогда не давал речи, «мико» не распознавалось."""
    sr = 16000
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.0005, sr // 2)                              # полсекунды фона
    speech = 0.02 * np.sin(2 * np.pi * 200 * np.arange(sr) / sr)        # секунда тихой речи
    x = np.concatenate([noise, speech]).astype(np.float32)
    thr = VT.adaptive_thresh(x, sr)
    check(VT.has_speech(x, sr, thr), "тихая речь над фоном должна распознаваться")
    check(not VT.has_speech(noise, sr, VT.adaptive_thresh(noise, sr)), "один фон — не речь")
    check(VT.adaptive_thresh(x, sr, sens=2.0) < thr, "чувствительность выше — порог ниже")

def test_wake_words_are_configurable_and_default_to_mico():
    check(VT.wake_word_list("") == VT.WAKE_WORDS and VT.wake_word_list("  ") == VT.WAKE_WORDS)
    check(VT.wake_word_list("Ассистент, Алиса") == {"ассистент", "алиса"}, VT.wake_word_list("Ассистент, Алиса"))
    check(VT.after_wake("Алиса, включи музыку", VT.wake_word_list("алиса")) == "включи музыку")
    check(VT.after_wake("Алиса, привет", VT.wake_word_list("мико")) is None, "чужое имя не будит")
    check(VT.after_wake("Мико?", None) == "", "вопросительный знак после имени")

def test_tune_applies_every_voice_setting():
    base = VT.tune("idle", {})
    check(abs(base["length"] - 1.0) < 1e-6 and abs(base["volume"] - 1.0) < 1e-6 and base["pause"] == 1.0)
    fast = VT.tune("idle", {"voice_speed": 1.5})
    check(fast["length"] < base["length"], "скорость 150% — короче по времени")
    loud = VT.tune("idle", {"voice_volume": 150})
    check(abs(loud["volume"] - 1.5) < 1e-6, "громкость 150%")
    alive = VT.tune("idle", {"voice_expr": 100})
    dead = VT.tune("idle", {"voice_expr": 0})
    check(alive["noise"] > dead["noise"] and alive["noise_w"] > dead["noise_w"], "выразительность")
    flat = VT.tune("excited", {"voice_mood": False})
    check(flat == VT.tune("idle", {}), "без настроения — обычный голос")
    long_pause = VT.tune("idle", {"voice_pause": 2.0})
    check(long_pause["pause"] == 2.0 and VT.tune("idle", {"voice_pause": 99})["pause"] == 2.0, "паузы ограничены")
    check(VT.tune("idle", {"voice_speed": 0.01})["length"] <= 1.0 / 0.5 + 1e-6, "скорость не уходит в ноль")

def test_settings_tab_is_wired_and_defaults_match():
    import ast
    vs = open(_os.path.join(ROOT, "voice_settings.py"), encoding="utf-8").read()
    main = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    check('tabs.addTab(self._voice.pages(), i18n.t("Голос"), "speaker")' in main, "вкладка «Голос» в настройках")
    check("self._voice.apply(self.cfg)" in main, "вкладка сохраняется при «Сохранить»")
    for key in ["voice_on", "voice_name", "voice_mood", "voice_speed", "voice_expr", "voice_pause", "voice_volume",
                "voice_wake", "voice_wake_words", "voice_wake_sens", "voice_end_ms", "voice_mic"]:
        check(f'"{key}"' in main, f"нет значения по умолчанию в main: {key}")
        check(f'"{key}"' in vs, f"вкладка не использует {key}")
    check("voice_ctl.shared(cfg)" in vs and "voice_ctl.shared(cfg)" in open(_os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read(),
          "чат и настройки должны использовать один голосовой контроллер")
    check("self.voice.heard.connect(self._voice_heard)" in open(_os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read(),
          "строка «Слышу» подключена")
    vc = open(_os.path.join(ROOT, "voice_ctl.py"), encoding="utf-8").read()
    check("def test_mic" in vc and "test_result.emit" in vc and "def test_voice" in vc, "проверки голоса и микрофона")
    check("adaptive_thresh" in vc and "voice_wake_words" in vc or "_wake_words" in vc, "настройки применяются в контроллере")




def test_controller_picks_engine_and_avoids_reload_loop():
    vc = open(_os.path.join(ROOT, "voice_ctl.py"), encoding="utf-8").read()
    check("def _engine_for" in vc and "PiperRu" in vc, "движок Piper")
    check("cur.model_path == model" in vc, "тот же файл модели не перезагружаем")
    check("self._attempt != self.voice_name()" in vc, "повтор загрузки только при смене голоса во время загрузки")
    check("tts.synth(sent, t)" in vc, "единый интерфейс синтеза")


# ---------- журнал ошибок ----------

def test_error_log_keeps_traceback_and_returns_short_text():
    import voice_log
    try:
        raise NameError("name 'obj' is not defined")
    except NameError as e:
        msg = voice_log.record("Голос не запустился", e)
    check("NameError" in msg and "voice_error.log" in msg, msg)
    check(_os.path.exists(voice_log.LOG_PATH), "журнал создан")
    with open(voice_log.LOG_PATH, encoding="utf-8") as f:
        check("Traceback" in f.read(), "трейсбек записан")


# ---------- windowed exe: стандартные потоки ----------
def test_frozen_exe_has_stdio_fallback_before_imports():
    src = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    head = src[:src.index("import storage") if "import storage" in src else 1500]
    check("if _sys.stdout is None:" in src and "if _sys.stderr is None:" in src, "подмена None-потоков")
    check(src.index("_sys.stdout is None") < src.index("from storage") if "from storage" in src else True,
          "подмена до импортов приложения")

if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:
                fails += 1
                print("FAIL", name, "-", e)
    print("ALL OK voice" if not fails else f"FAILED {fails}")
    sys.exit(1 if fails else 0)


# ---------- RHVoice (GPL-3.0): через консольную утилиту, без установки в проект ----------
def test_rhvoice_is_not_downloaded_and_needs_install():
    real = VM.rhvoice_exe
    try:
        VM.rhvoice_exe = lambda: None
        check(not VM.is_installed("rv_anna"), "без RHVoice голос не установлен")
        try:
            VM.download("rv_anna")
            check(False, "скачивание RHVoice не должно выполняться")
        except RuntimeError as e:
            check("rhvoice.org" in str(e), "подсказка со ссылкой на установку")
    finally:
        VM.rhvoice_exe = real


def test_rhvoice_engine_passes_text_on_stdin_and_reads_wav():
    import voice_tts
    src = open(_os.path.join(ROOT, "voice_tts.py"), encoding="utf-8").read()
    check("class RHVoiceRu" in src and "input=text.encode(\"utf-8\")" in src, "текст передаётся на stdin")
    check("\"-p\", self.speaker" in src, "голос выбирается флагом -p")
    check("RHVOICE_OUT_ARG" in src, "флаг записи WAV вынесен в одну константу")
    check("creationflags=flags" in src, "без окна консоли на Windows")
    check(hasattr(voice_tts, "RHVoiceRu"), "класс доступен")


def test_controller_uses_rhvoice_engine_for_rhvoice_voices():
    vc = open(_os.path.join(ROOT, "voice_ctl.py"), encoding="utf-8").read()
    check('voice_models.engine(name) == "rhvoice"' in vc and "RHVoiceRu(voice_models.rhvoice_exe(), speaker)" in vc,
          "для голосов RHVoice выбирается движок RHVoice")
    dock = open(_os.path.join(ROOT, "voice_dock.py"), encoding="utf-8").read()
    check("for i in range(0, len(items), 4):" in dock, "голоса в панели — рядами по четыре")

