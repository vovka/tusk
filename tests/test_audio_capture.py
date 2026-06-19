from contextlib import contextmanager
import types

import shells.voice.stages.audio_capture as audio_capture
from shells.voice.stages.audio_capture import AudioCapture


def _gate() -> object:
    checks = [True, False, True]
    return types.SimpleNamespace(wait=lambda: None, is_set=lambda: checks.pop(0))


@contextmanager
def _stream(state: object) -> object:
    yield types.SimpleNamespace(read=lambda frame_size: (b"a", None))
    state.closed = True


def test_capture_closes_stream_before_waiting_for_resume(monkeypatch: object) -> None:
    all_states = [types.SimpleNamespace(closed=False), types.SimpleNamespace(closed=False)]
    states = all_states.copy()
    monkeypatch.setattr(audio_capture, "sd", types.SimpleNamespace(RawInputStream=lambda **kwargs: _stream(states.pop(0))))
    frames = AudioCapture(1000, 10, _gate()).stream_frames()
    assert next(frames) == b"a"
    assert next(frames) == b"a"
    assert states == []
    assert all_states[0].closed
