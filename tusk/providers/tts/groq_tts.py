try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

from tusk.shared.tts.interfaces.tts_engine import TTSEngine

__all__ = ["GroqTTS"]


class GroqTTS(TTSEngine):
    def __init__(self, api_key: str, model: str = "canopylabs/orpheus-v1-english", voice: str = "daniel") -> None:
        if Groq is None:
            raise RuntimeError("groq package is not installed")
        self._client = Groq(api_key=api_key)
        self._model = model
        self._voice = voice

    def synthesize(self, text: str) -> bytes:
        response = self._client.audio.speech.create(
            model=self._model,
            voice=self._voice,
            input=text,
            response_format="wav",
        )
        return response.read()
