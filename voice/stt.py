"""Распознавание речи: faster-whisper (Whisper в CTranslate2), только локально, только русский."""
import numpy as np

from voice import models as voice_models


def _repo():
    """Адрес модели распознавания на Hugging Face (тот же, что берёт faster-whisper)."""
    name = voice_models.WHISPER_MODEL
    try:
        from faster_whisper.utils import _MODELS
        return _MODELS.get(name, name)
    except Exception:
        return "Systran/faster-whisper-" + name


_PATTERNS = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]


def is_cached():
    """Модель распознавания уже скачана на диск?"""
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(_repo(), allow_patterns=_PATTERNS, cache_dir=voice_models.WHISPER_DIR, local_files_only=True)
        return True
    except Exception:
        return False


def prefetch(progress):
    """Скачивает модель распознавания и сообщает долю 0…1 по общему размеру файлов. Раньше скачивание шло молча,
    и в голосовом режиме не было видно, сколько осталось. Любая ошибка не страшна: тогда модель скачает сама библиотека,
    просто без процентов."""
    try:
        from huggingface_hub import snapshot_download
        from tqdm.auto import tqdm
    except Exception:
        return False
    bars = set()

    def report():
        tot = sum(b.total or 0 for b in bars if getattr(b, "unit", "") == "B")
        done = sum(b.n or 0 for b in bars if getattr(b, "unit", "") == "B")
        if tot > 0:
            progress(max(0.0, min(1.0, done / tot)))

    class _Bar(tqdm):
        def __init__(self, *a, **k):
            k.pop("name", None)
            super().__init__(*a, **{**k, "disable": False})
            bars.add(self)

        def update(self, n=1):
            r = super().update(n)
            try:
                report()
            except Exception:
                pass
            return r

    try:
        snapshot_download(_repo(), allow_patterns=_PATTERNS, cache_dir=voice_models.WHISPER_DIR, tqdm_class=_Bar)
        return True
    except Exception:
        return False


class WhisperRu:
    def __init__(self):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(voice_models.WHISPER_MODEL, device="cpu", compute_type="int8",
                                  download_root=voice_models.WHISPER_DIR)

    def transcribe(self, audio16k):
        """Запись 16 кГц mono float32 → текст. Встроенный VAD пропускает тишину."""
        segments, _ = self.model.transcribe(np.asarray(audio16k, dtype=np.float32), language="ru",
                                            beam_size=1, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
