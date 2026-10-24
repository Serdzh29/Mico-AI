"""Синтез речи: Piper — русские голоса в .onnx, без PyTorch и без системных голосов Windows.
Интерфейс: synth(text, tune) -> (звук float32, частота)."""
import io
import wave

import numpy as np


class PiperRu:
    def __init__(self, onnx_path, conf_path):
        from piper import PiperVoice
        self.model_path = onnx_path
        self.voice = PiperVoice.load(onnx_path, config_path=conf_path)
        self.sample_rate = int(self.voice.config.sample_rate)

    def synth(self, text, tune):
        length, noise, noise_w = tune["length"], tune["noise"], tune["noise_w"]
        try:
            from piper import SynthesisConfig           # новые сборки piper-tts (1.3+)
        except ImportError:
            SynthesisConfig = None
        if SynthesisConfig is not None:
            syn = SynthesisConfig(length_scale=length, noise_scale=noise, noise_w_scale=noise_w)
            pieces = [np.asarray(c.audio_float_array, dtype=np.float32).reshape(-1)
                      for c in self.voice.synthesize(text, syn_config=syn)]
            audio = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
        else:                                            # старые сборки (1.2.x)
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                self.voice.synthesize(text, w, length_scale=length, noise_scale=noise, noise_w=noise_w)
            buf.seek(0)
            with wave.open(buf, "rb") as r:
                raw = r.readframes(r.getnframes())
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return audio, self.sample_rate


# Какой аргумент RHVoice-test пишет результат в WAV-файл. Проверено только на Windows-установке — поправить здесь.
RHVOICE_OUT_ARG = "-o"


class RHVoiceRu:
    """Голос RHVoice (GPL-3.0): текст подаётся на stdin консольной утилиты RHVoice-test, результат — WAV.
    Громкость и скорость задаются самим RHVoice; тон/шум Piper здесь не применяются."""

    def __init__(self, exe, speaker):
        self.exe = exe
        self.speaker = speaker
        self.model_path = f"rhvoice:{speaker}"       # для сравнения «тот же голос уже загружен»
        self.sample_rate = 0

    def synth(self, text, tune):
        import os
        import subprocess
        import tempfile
        import wave
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)     # на Windows — без чёрного окна консоли
            subprocess.run([self.exe, "-p", self.speaker, RHVOICE_OUT_ARG, path],
                           input=text.encode("utf-8"), check=True, timeout=60, creationflags=flags)
            with wave.open(path, "rb") as r:
                sr = r.getframerate()
                ch = r.getnchannels()
                width = r.getsampwidth()
                raw = r.readframes(r.getnframes())
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
        if width != 2:
            raise RuntimeError("RHVoice вернул не 16-битный WAV")
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            audio = audio.reshape(-1, ch).mean(axis=1)
        return audio, sr

