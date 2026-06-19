from collections.abc import Iterator

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover
    sd = None

__all__ = ["AudioCapture"]


class AudioCapture:
    def __init__(self, sample_rate: int, frame_duration_ms: int, pause_gate: object | None = None) -> None:
        if sd is None:
            raise RuntimeError("sounddevice package is not installed")
        self._sample_rate = sample_rate
        self._frame_size = int(sample_rate * frame_duration_ms / 1000)
        self._pause_gate = pause_gate

    def stream_frames(self) -> Iterator[bytes]:
        while True:
            self._await_resume()
            with self._open_stream() as stream:
                while self._is_resumed():
                    data, _ = stream.read(self._frame_size)
                    yield bytes(data)

    def _is_resumed(self) -> bool:
        return self._pause_gate is None or self._pause_gate.is_set()

    def _open_stream(self) -> object:
        return sd.RawInputStream(samplerate=self._sample_rate, blocksize=self._frame_size, dtype="int16", channels=1)

    def _await_resume(self) -> None:
        if self._pause_gate is not None:
            self._pause_gate.wait()
