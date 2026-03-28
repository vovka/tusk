from tusk.kernel.hallucination_filter import HallucinationFilter
from tusk.kernel.schemas.utterance import Utterance


def _utterance(text: str, duration: float = 1.0) -> Utterance:
    return Utterance(text=text, audio_frames=b"", duration_seconds=duration)


def test_rejects_ghost_phrase() -> None:
    assert not HallucinationFilter().is_valid(_utterance("Thank you."))


def test_rejects_punctuation_only() -> None:
    assert not HallucinationFilter().is_valid(_utterance("."))


def test_rejects_short_duration() -> None:
    assert not HallucinationFilter().is_valid(_utterance("hi", duration=0.2))


def test_accepts_desktop_command() -> None:
    assert HallucinationFilter().is_valid(_utterance("open Firefox"))
