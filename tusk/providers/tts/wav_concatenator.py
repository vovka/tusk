import io
import wave

__all__ = ["WavConcatenator"]


class WavConcatenator:
    def concatenate(self, clips: list[bytes]) -> bytes:
        if len(clips) == 1:
            return clips[0]
        buffer = io.BytesIO()
        writer = self._open_writer(buffer, clips[0])
        for clip in clips:
            writer.writeframes(self._frames(clip))
        writer.close()
        return buffer.getvalue()

    def _open_writer(self, buffer: io.BytesIO, sample: bytes) -> wave.Wave_write:
        writer = wave.open(buffer, "wb")
        with wave.open(io.BytesIO(sample), "rb") as reader:
            # Skip setparams: a streamed clip declares a placeholder frame count
            # that would overflow the output header's size field.
            writer.setnchannels(reader.getnchannels())
            writer.setsampwidth(reader.getsampwidth())
            writer.setframerate(reader.getframerate())
        return writer

    def _frames(self, clip: bytes) -> bytes:
        with wave.open(io.BytesIO(clip), "rb") as reader:
            return reader.readframes(reader.getnframes())
