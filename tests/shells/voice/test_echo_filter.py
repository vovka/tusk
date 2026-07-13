from shells.voice.stages.echo_filter import EchoFilter
from tusk.shared.schemas.utterance import Utterance


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _filter(recent: list[tuple[str, float]], now: float = 100.0) -> EchoFilter:
    return EchoFilter(lambda: recent, None, now=lambda: now)


def test_exact_echo_is_dropped() -> None:
    echo = _filter([("Switching to PowerPoint.", 100.0)])
    assert echo.process(_utterance("Switching to PowerPoint.")) is None


def test_case_and_punctuation_variant_is_dropped() -> None:
    echo = _filter([("Switching to PowerPoint.", 99.0)])
    assert echo.process(_utterance("switching to powerpoint")) is None


def test_concatenated_recent_texts_are_dropped() -> None:
    recent = [("PowerPoint is now the active window.", 98.0), ("Switching to PowerPoint.", 99.0)]
    merged = "PowerPoint is now the active window. Switching to PowerPoint."
    assert _filter(recent).process(_utterance(merged)) is None


def test_unrelated_utterance_passes() -> None:
    echo = _filter([("Switching to PowerPoint.", 100.0)])
    assert echo.process(_utterance("open gedit and write a poem")) is not None


def test_speech_outside_window_passes() -> None:
    echo = _filter([("Switching to PowerPoint.", 80.0)], now=100.0)
    assert echo.process(_utterance("Switching to PowerPoint.")) is not None


def test_no_recent_speech_passes() -> None:
    assert _filter([]).process(_utterance("Switching to PowerPoint.")) is not None


def test_short_command_similar_to_recent_speech_is_kept() -> None:
    echo = _filter([("step", 100.0)])
    assert echo.process(_utterance("stop")) is not None


def test_short_exact_echo_is_still_dropped() -> None:
    echo = _filter([("Stop.", 100.0)])
    assert echo.process(_utterance("stop")) is None
