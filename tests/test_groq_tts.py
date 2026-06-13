import types
from unittest.mock import patch

from tusk.providers.tts import GroqTTS

_VOICES = {"autumn", "diana", "hannah", "austin", "daniel", "troy"}


def test_groq_tts_synthesizes_wav_bytes() -> None:
    assert GroqTTS("test-key").synthesize("hello there") == b"WAVDATA"


def test_groq_tts_uses_supported_model_and_wav_format() -> None:
    captured: dict[str, object] = {}
    with patch("tusk.providers.tts.groq_tts.Groq", return_value=_recording_client(captured)):
        GroqTTS("test-key").synthesize("hello there")
    assert captured["model"] == "canopylabs/orpheus-v1-english"
    assert captured["response_format"] == "wav"
    assert captured["voice"] in _VOICES


def _recording_client(captured: dict[str, object]) -> object:
    def create(**kwargs: object) -> object:
        captured.update(kwargs)
        return types.SimpleNamespace(read=lambda: b"WAVDATA")

    return types.SimpleNamespace(audio=types.SimpleNamespace(speech=types.SimpleNamespace(create=create)))
