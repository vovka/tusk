import types

from tts_engine_builder import TtsEngineBuilder
from tusk.providers.tts import OpenAICompatibleTTS


def test_builds_groq_tts_when_url_unset(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr("tts_engine_builder.GroqTTS", lambda key: sentinel)
    assert TtsEngineBuilder(_config("")).build() is sentinel


def test_builds_openai_compatible_tts_when_url_set() -> None:
    engine = TtsEngineBuilder(_config("http://kokoro:8880/v1/audio/speech")).build()
    assert isinstance(engine, OpenAICompatibleTTS)


def _config(tts_url: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(groq_api_key="k", tts_url=tts_url, tts_model="kokoro", tts_voice="am_michael")
