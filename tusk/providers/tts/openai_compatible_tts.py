import json
from collections.abc import Iterator
from urllib.request import Request, urlopen

from tusk.providers.tts.text_chunker import TextChunker
from tusk.shared.interfaces.tts_engine import TTSEngine

__all__ = ["OpenAICompatibleTTS"]

_MAX_INPUT_CHARS = 200
_TIMEOUT_SECONDS = 30.0


class OpenAICompatibleTTS(TTSEngine):
    """POSTs to an OpenAI-compatible /v1/audio/speech endpoint (e.g. a local Kokoro server)."""

    def __init__(self, url: str, model: str, voice: str) -> None:
        self._url = url
        self._model = model
        self._voice = voice
        self._chunker = TextChunker(_MAX_INPUT_CHARS)

    def synthesize_chunks(self, text: str) -> Iterator[bytes]:
        for chunk in self._chunker.split(text):
            yield self._synthesize_chunk(chunk)

    def _synthesize_chunk(self, text: str) -> bytes:
        payload = {"model": self._model, "input": text, "voice": self._voice, "response_format": "wav"}
        request = Request(self._url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
        with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return response.read()
