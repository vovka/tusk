import numpy as np
import whisper

from tusk.interfaces.stt_engine import STTEngine
from tusk.schemas.utterance import Utterance

__all__ = ["WhisperSTT"]


class WhisperSTT(STTEngine):
    def __init__(self, model_size: str) -> None:
        self._model = whisper.load_model(model_size)

    def transcribe(self, audio_frames: bytes, sample_rate: int) -> Utterance:
        audio_array = self._decode_pcm(audio_frames)
        result = self._model.transcribe(audio_array, fp16=False, language="en")
        text = result["text"].strip()
        duration = len(audio_frames) / (sample_rate * 2)
        confidence = self._compute_confidence(result.get("segments", []))
        return Utterance(text=text, audio_frames=audio_frames, duration_seconds=duration, confidence=confidence)

    def _compute_confidence(self, segments: list) -> float:
        if not segments:
            return 0.0
        avg_logprob = sum(s.get("avg_logprob", -1.0) for s in segments) / len(segments)
        no_speech_prob = max(s.get("no_speech_prob", 0.0) for s in segments)
        logprob_score = min(1.0, max(0.0, (avg_logprob + 1.0) / 1.0))
        return logprob_score * (1.0 - no_speech_prob)

    def _decode_pcm(self, audio_frames: bytes) -> np.ndarray:
        pcm = np.frombuffer(audio_frames, dtype=np.int16)
        return pcm.astype(np.float32) / 32768.0
