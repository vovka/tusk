import io
import re
import wave

from groq import Groq

from tusk.interfaces.stt_engine import STTEngine
from tusk.schemas.utterance import Utterance

__all__ = ["GroqSTT"]

_HALLUCINATION = re.compile(r"^\[.+\]$")  # e.g. [BLANK_AUDIO], [Music], [Applause]


class GroqSTT(STTEngine):
    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo") -> None:
        self._client = Groq(api_key=api_key)
        self._model = model

    def transcribe(self, audio_frames: bytes, sample_rate: int) -> Utterance:
        wav_bytes = self._pcm_to_wav(audio_frames, sample_rate)
        text = self._call_api(wav_bytes)
        duration = len(audio_frames) / (sample_rate * 2)
        confidence = 0.0 if self._is_non_speech(text) else 1.0
        return Utterance(text=text, audio_frames=audio_frames, duration_seconds=duration, confidence=confidence)

    def _call_api(self, wav_bytes: bytes) -> str:
        response = self._client.audio.transcriptions.create(
            file=("audio.wav", wav_bytes),
            model=self._model,
            language="en",
        )
        return response.text.strip()

    def _pcm_to_wav(self, pcm: bytes, sample_rate: int) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()

    def _is_non_speech(self, text: str) -> bool:
        return not text or bool(_HALLUCINATION.match(text))
