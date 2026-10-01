import types

from tusk.providers.stt import groq_stt
from tusk.providers.stt.groq_stt import GroqSTT


class _FakeTranscriptions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs) -> types.SimpleNamespace:
        self.calls.append(kwargs)
        return types.SimpleNamespace(text="hi")


def _engine(monkeypatch, vocabulary: str) -> tuple[GroqSTT, _FakeTranscriptions]:
    transcriptions = _FakeTranscriptions()
    client = types.SimpleNamespace(audio=types.SimpleNamespace(transcriptions=transcriptions))
    monkeypatch.setattr(groq_stt, "Groq", lambda api_key: client)
    return GroqSTT("key", vocabulary=vocabulary), transcriptions


def test_groq_passes_vocabulary_as_prompt(monkeypatch) -> None:
    engine, transcriptions = _engine(monkeypatch, "gedit, firefox")
    engine.transcribe(b"\x00\x00" * 10, 16000)
    assert transcriptions.calls[0]["prompt"] == "gedit, firefox"


def test_groq_omits_prompt_without_vocabulary(monkeypatch) -> None:
    engine, transcriptions = _engine(monkeypatch, "")
    engine.transcribe(b"\x00\x00" * 10, 16000)
    assert "prompt" not in transcriptions.calls[0]


def test_groq_trims_vocabulary_to_the_api_prompt_limit(monkeypatch) -> None:
    engine, transcriptions = _engine(monkeypatch, ", ".join(f"application{i}" for i in range(200)))
    engine.transcribe(b"\x00\x00" * 10, 16000)
    prompt = transcriptions.calls[0]["prompt"]
    assert len(prompt) <= 896
    assert not prompt.endswith(",")
