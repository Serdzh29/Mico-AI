"""Распознавание речи: faster-whisper (Whisper в CTranslate2), только локально, только русский."""
import numpy as np

import voice_models


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
