import io
import types
import wave
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


def test_groq_tts_chunks_long_input_under_orpheus_limit() -> None:
    inputs: list[str] = []
    with patch("tusk.providers.tts.groq_tts.Groq", return_value=_chunk_client(inputs, _wav_bytes(b"\x01\x02"))):
        result = GroqTTS("test-key").synthesize("word " * 100)
    assert len(inputs) > 1
    assert all(len(chunk) <= 200 for chunk in inputs)
    assert _wav_frames(result) == b"\x01\x02" * len(inputs)


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


def _wav_bytes(frames: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(24000)
        writer.writeframes(frames)
    return buffer.getvalue()


def _wav_frames(data: bytes) -> bytes:
    with wave.open(io.BytesIO(data), "rb") as reader:
        return reader.readframes(reader.getnframes())
