import types

from shells.voice.stages import utterance_detector


def test_detector_logs_completed_utterance(monkeypatch) -> None:
    logs: list[tuple[str, str, str]] = []
    monkeypatch.setattr(utterance_detector, "webrtcvad", types.SimpleNamespace(Vad=_FakeVad))
    detector = utterance_detector.UtteranceDetector(_audio(), 16000, 2, _log(logs))
    assert len(list(detector.stream_utterances())) == 1
    assert logs == [
        ("DETECTOR", "speech started", "detector"),
        ("DETECTOR", "utterance complete (5 frames)", "detector"),
    ]


def test_utterance_duration_uses_configured_frame_length(monkeypatch) -> None:
    monkeypatch.setattr(utterance_detector, "webrtcvad", types.SimpleNamespace(Vad=_FakeVad))
    detector = utterance_detector.UtteranceDetector(_audio(), 16000, 2, _log([]), frame_duration_ms=20)
    utterance = next(detector.stream_utterances())
    assert utterance.duration_seconds == 5 * 0.020


def test_isolated_speech_blip_does_not_restart_silence(monkeypatch) -> None:
    monkeypatch.setattr(utterance_detector, "webrtcvad", types.SimpleNamespace(Vad=_FakeVad))
    frames = [b"speech"] * 5 + [b"silence"] * 15 + [b"speech"] + [b"silence"] * 15
    audio = types.SimpleNamespace(stream_frames=lambda: iter(frames))
    detector = utterance_detector.UtteranceDetector(audio, 16000, 2, _log([]))
    assert len(list(detector.stream_utterances())) == 1


class _FakeVad:
    def __init__(self, aggressiveness: int) -> None:
        self._aggressiveness = aggressiveness

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        return frame == b"speech"


def _audio() -> object:
    frames = [b"speech"] * 5 + [b"silence"] * 20
    return types.SimpleNamespace(stream_frames=lambda: iter(frames))


def _log(logs: list[tuple[str, str, str]]) -> object:
    return types.SimpleNamespace(log=lambda *args: logs.append(args))
