from tusk.providers.stt.groq_stt import GroqSTT
from tusk.providers.stt.whisper_stt import WhisperSTT
from tusk.shared.stt.interfaces.stt_engine import STTEngine

__all__ = ["STTEngineFactory"]


class STTEngineFactory:
    def __init__(self, groq_api_key: str, whisper_model_size: str) -> None:
        self._groq_api_key = groq_api_key
        self._whisper_model_size = whisper_model_size

    def create(self, name: str) -> STTEngine:
        if name == "whisper":
            return WhisperSTT(self._whisper_model_size)
        if name == "groq":
            return GroqSTT(self._groq_api_key)
        raise ValueError(f"unknown STT_ENGINE: {name!r}")
