import types
from unittest.mock import patch

from tusk.providers.tts import GroqTTS

_VOICES = {"autumn", "diana", "hannah", "austin", "daniel", "troy"}


def test_groq_tts_yields_wav_bytes() -> None:
    assert list(GroqTTS("test-key").synthesize_chunks("hello there")) == [b"WAVDATA"]


def test_groq_tts_uses_supported_model_and_wav_format() -> None:
    captured: dict[str, object] = {}
    with patch("tusk.providers.tts.groq_tts.Groq", return_value=_recording_client(captured)):
        list(GroqTTS("test-key").synthesize_chunks("hello there"))
    assert captured["model"] == "canopylabs/orpheus-v1-english"
    assert captured["response_format"] == "wav"
    assert captured["voice"] in _VOICES


def test_groq_tts_yields_one_clip_per_chunk_under_orpheus_limit() -> None:
    inputs: list[str] = []
    with patch("tusk.providers.tts.groq_tts.Groq", return_value=_chunk_client(inputs, b"CLIP")):
        clips = list(GroqTTS("test-key").synthesize_chunks("word " * 100))
    assert len(clips) == len(inputs) > 1
    assert all(len(chunk) <= 200 for chunk in inputs)
    assert clips == [b"CLIP"] * len(inputs)


def test_groq_tts_synthesizes_lazily_per_chunk() -> None:
    inputs: list[str] = []
    with patch("tusk.providers.tts.groq_tts.Groq", return_value=_chunk_client(inputs, b"CLIP")):
        chunks = GroqTTS("test-key").synthesize_chunks("word " * 100)
        next(chunks)
    assert len(inputs) == 1


def _recording_client(captured: dict[str, object]) -> object:
    def create(**kwargs: object) -> object:
        captured.update(kwargs)
        return types.SimpleNamespace(read=lambda: b"WAVDATA")

    return types.SimpleNamespace(audio=types.SimpleNamespace(speech=types.SimpleNamespace(create=create)))


def _chunk_client(inputs: list[str], clip: bytes) -> object:
    def create(**kwargs: object) -> object:
        inputs.append(str(kwargs["input"]))
        return types.SimpleNamespace(read=lambda: clip)

    return types.SimpleNamespace(audio=types.SimpleNamespace(speech=types.SimpleNamespace(create=create)))
