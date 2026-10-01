import pytest

from tusk.providers.stt import stt_engine_factory
from tusk.providers.stt.stt_engine_factory import STTEngineFactory


def _factory() -> STTEngineFactory:
    return STTEngineFactory("groq-key", "base")


def test_creates_groq_engine_by_name(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr(stt_engine_factory, "GroqSTT", lambda key, vocabulary: sentinel)
    assert _factory().create("groq") is sentinel


def test_creates_whisper_engine_by_name(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr(stt_engine_factory, "WhisperSTT", lambda model_size, vocabulary: sentinel)
    assert _factory().create("whisper") is sentinel


def test_rejects_unknown_engine_name() -> None:
    with pytest.raises(ValueError):
        _factory().create("bogus")


def test_factory_passes_vocabulary_to_engines(monkeypatch) -> None:
    monkeypatch.setattr(stt_engine_factory, "GroqSTT", lambda key, vocabulary: vocabulary)
    assert STTEngineFactory("groq-key", "base", "gedit").create("groq") == "gedit"
