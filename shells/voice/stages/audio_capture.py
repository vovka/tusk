from collections.abc import Iterator

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover
    sd = None

__all__ = ["AudioCapture"]


class AudioCapture:
    def __init__(self, sample_rate: int, frame_duration_ms: int) -> None:
        if sd is None:
            raise RuntimeError("sounddevice package is not installed")
        self._sample_rate = sample_rate
        self._frame_size = int(sample_rate * frame_duration_ms / 1000)

    def stream_frames(self) -> Iterator[bytes]:
        with sd.RawInputStream(
            samplerate=self._sample_rate,
            blocksize=self._frame_size,
            dtype="int16",
            channels=1,
        ) as stream:
            while True:
                data, _ = stream.read(self._frame_size)
                yield bytes(data)
