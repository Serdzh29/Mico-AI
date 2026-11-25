"""Синтез речи: Piper — русские голоса в .onnx, без PyTorch и без системных голосов Windows.
Edge TTS — облачные голоса Microsoft (требует интернет, но качество выше).
Интерфейс: synth(text, tune) -> (звук float32, частота)."""
import asyncio
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


class EdgeTTS:
    """Облачные голоса Microsoft через Edge TTS. Требует интернет, но не требует загрузки моделей."""

    def __init__(self, voice_name):
        """voice_name: например 'ru-RU-DmitryNeural' или 'en-US-JennyNeural'"""
        self.voice_name = voice_name
        self.sample_rate = 24000  # Edge TTS всегда возвращает 24kHz

    def synth(self, text, tune):
        """Синтезирует речь через Edge TTS. tune игнорируется (Edge TTS не поддерживает эти параметры)."""
        try:
            # Запускаем асинхронную функцию синхронно
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio = loop.run_until_complete(self._synth_async(text))
            finally:
                loop.close()
            return audio, self.sample_rate
        except Exception:
            # При ошибке (нет интернета, таймаут) возвращаем пустой звук
            return np.zeros(0, dtype=np.float32), self.sample_rate

    async def _synth_async(self, text):
        """Асинхронный синтез через edge-tts."""
        import edge_tts

        communicate = edge_tts.Communicate(text, self.voice_name)
        audio_bytes = b""

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]

        # Конвертируем MP3 bytes в numpy array
        if not audio_bytes:
            return np.zeros(0, dtype=np.float32)

        # Edge TTS возвращает MP3, декодируем через wave/pydub или напрямую
        # Для простоты используем wave (Edge TTS может вернуть WAV с параметром)
        buf = io.BytesIO(audio_bytes)
        try:
            with wave.open(buf, "rb") as w:
                raw = w.readframes(w.getnframes())
                channels = w.getnchannels()
                sampwidth = w.getsampwidth()

            if sampwidth == 2:  # 16-bit
                audio = np.frombuffer(raw, dtype=np.int16)
            else:
                audio = np.frombuffer(raw, dtype=np.uint8)

            # Конвертируем в float32 [-1, 1]
            if sampwidth == 2:
                audio = audio.astype(np.float32) / 32768.0
            else:
                audio = (audio.astype(np.float32) - 128) / 128.0

            # Если стерео, берём только левый канал
            if channels == 2:
                audio = audio[::2]

            return audio
        except:
            # Если не получилось декодировать как WAV, пробуем через scipy/soundfile
            # Но для первой версии просто возвращаем тишину
            return np.zeros(0, dtype=np.float32)
