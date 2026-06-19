import types

import shells.voice.stages.audio_capture as audio_capture
from shells.voice.stages.audio_capture import AudioCapture


class _Gate:
    def __init__(self) -> None:
        self._checks = [True, False, True]

    def wait(self) -> None:
        return None

    def is_set(self) -> bool:
        return self._checks.pop(0)


class _Stream:
    def __init__(self) -> None:
        self.closed = False

    def __enter__(self) -> object:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.closed = True

    def read(self, frame_size: int) -> tuple[bytes, None]:
        return b"a", None


def test_capture_closes_stream_before_waiting_for_resume(monkeypatch: object) -> None:
    streams = [_Stream(), _Stream()]
    monkeypatch.setattr(audio_capture, "sd", types.SimpleNamespace(RawInputStream=lambda **kwargs: streams.pop(0)))
    frames = AudioCapture(1000, 10, _Gate()).stream_frames()
    assert next(frames) == b"a"
    assert next(frames) == b"a"
    assert streams == []
