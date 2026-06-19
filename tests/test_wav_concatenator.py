import io
import struct
import wave

from tusk.providers.tts.wav_concatenator import WavConcatenator


def test_concatenate_handles_streaming_clip_header_without_overflow() -> None:
    clip = _forge_streaming_header(_wav_bytes(b"\x01\x02\x03\x04"))
    result = WavConcatenator().concatenate([clip, clip])
    assert _wav_frames(result) == b"\x01\x02\x03\x04" * 2


def _forge_streaming_header(wav: bytes) -> bytes:
    # Orpheus streams the clip, so its header declares a placeholder data size.
    size_pos = wav.index(b"data") + 4
    return wav[:size_pos] + struct.pack("<L", 0xFFFFFFFF) + wav[size_pos + 4:]


def _wav_bytes(frames: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(24000)
        writer.writeframes(frames)
    return buffer.getvalue()


def _wav_frames(data: bytes) -> bytes:
    with wave.open(io.BytesIO(data), "rb") as reader:
        return reader.readframes(reader.getnframes())
