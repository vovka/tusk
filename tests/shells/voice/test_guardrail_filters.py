import types

from shells.voice.stages.sanitizer import Sanitizer
from tusk.shared.schemas.utterance import Utterance


def _utterance(text: str, duration: float = 1.0) -> Utterance:
    return Utterance(text=text, audio_frames=b"", duration_seconds=duration)


def test_rejects_ghost_phrase() -> None:
    assert Sanitizer().process(_utterance("Thank you.")) is None


def test_rejects_punctuation_only() -> None:
    assert Sanitizer().process(_utterance(".")) is None


def test_rejects_short_duration() -> None:
    assert Sanitizer().process(_utterance("hi", duration=0.2)) is None


def test_accepts_desktop_command() -> None:
    assert Sanitizer().process(_utterance("open Firefox")) == _utterance("open Firefox")


def test_sanitizer_logs_drop_reason() -> None:
    logs: list[tuple[str, str, str]] = []
    assert Sanitizer(_log(logs)).process(_utterance("Thank you.")) is None
    assert logs == [("SANITIZER", "dropped reason=ghost-phrase text='Thank you.'", "sanitizer")]


def test_sanitizer_logs_passed_text() -> None:
    logs: list[tuple[str, str, str]] = []
    utterance = _utterance("open Firefox")
    assert Sanitizer(_log(logs)).process(utterance) == utterance
    assert logs == [("SANITIZER", "passed text='open Firefox'", "sanitizer")]


def _log(logs: list[tuple[str, str, str]]) -> object:
    return types.SimpleNamespace(log=lambda *args: logs.append(args))
