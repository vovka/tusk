from collections.abc import Iterator

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

from tusk.providers.tts.text_chunker import TextChunker
from tusk.shared.tts.interfaces.tts_engine import TTSEngine

__all__ = ["GroqTTS"]

_MAX_INPUT_CHARS = 200


class GroqTTS(TTSEngine):
    def __init__(self, api_key: str, model: str = "canopylabs/orpheus-v1-english", voice: str = "daniel") -> None:
        if Groq is None:
            raise RuntimeError("groq package is not installed")
        self._client = Groq(api_key=api_key)
        self._model = model
        self._voice = voice
        self._chunker = TextChunker(_MAX_INPUT_CHARS)

    def synthesize_chunks(self, text: str) -> Iterator[bytes]:
        # ponytail: Orpheus caps `input` at 200 chars; each chunk is yielded as its own
        # WAV clip so playback can start after the first synthesis round trip.
        for chunk in self._chunker.split(text):
            yield self._synthesize_chunk(chunk)

    def _synthesize_chunk(self, text: str) -> bytes:
        response = self._client.audio.speech.create(
            model=self._model,
            voice=self._voice,
            input=text,
            response_format="wav",
        )
        return response.read()
