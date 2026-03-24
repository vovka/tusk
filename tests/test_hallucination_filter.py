from tusk.core.hallucination_filter import HallucinationFilter
from tusk.schemas.utterance import Utterance


def _utterance(text: str, duration: float = 1.0) -> Utterance:
    return Utterance(text=text, audio_frames=b"", duration_seconds=duration)


def test_rejects_thank_you() -> None:
    assert not HallucinationFilter().is_valid(_utterance("Thank you."))


def test_accepts_open_firefox() -> None:
    assert HallucinationFilter().is_valid(_utterance("open Firefox"))


def test_rejects_period_only() -> None:
    assert not HallucinationFilter().is_valid(_utterance("."))


def test_rejects_um() -> None:
    assert not HallucinationFilter().is_valid(_utterance("um"))


def test_rejects_short_duration() -> None:
    assert not HallucinationFilter().is_valid(_utterance("hi", duration=0.2))


def test_accepts_what_time_is_it() -> None:
    assert HallucinationFilter().is_valid(_utterance("what time is it"))


def test_rejects_empty() -> None:
    assert not HallucinationFilter().is_valid(_utterance(""))


def test_rejects_whitespace() -> None:
    assert not HallucinationFilter().is_valid(_utterance("   "))


def test_rejects_exclamation_only() -> None:
    assert not HallucinationFilter().is_valid(_utterance("!"))


def test_rejects_short_single_word() -> None:
    assert not HallucinationFilter().is_valid(_utterance("ah"))


def test_accepts_longer_single_word() -> None:
    assert HallucinationFilter().is_valid(_utterance("maximize"))
