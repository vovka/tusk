try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

from tusk.providers.tts.text_chunker import TextChunker
from tusk.providers.tts.wav_concatenator import WavConcatenator
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
        self._concatenator = WavConcatenator()

    def synthesize(self, text: str) -> bytes:
        # ponytail: Orpheus caps `input` at 200 chars, so multi-sentence replies are
        # spoken as several clips and merged into one WAV before playback.
        clips = [self._synthesize_chunk(chunk) for chunk in self._chunker.split(text)]
        return self._concatenator.concatenate(clips)

    def _synthesize_chunk(self, text: str) -> bytes:
        response = self._client.audio.speech.create(
            model=self._model,
            voice=self._voice,
            input=text,
            response_format="wav",
        )
        return response.read()
