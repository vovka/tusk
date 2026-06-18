import io
import struct
import types
import wave
from contextlib import nullcontext
from unittest.mock import patch

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


def test_wav_concatenator_ignores_source_declared_frame_count() -> None:
    writer = _recording_writer()
    reader = _reader_with_large_frame_count()

    with patch("tusk.providers.tts.wav_concatenator.wave.open", side_effect=[writer, nullcontext(reader)]):
        WavConcatenator()._open_writer(io.BytesIO(), b"WAV")

    assert writer.calls == [("channels", 1), ("width", 2), ("rate", 24000), ("compression", "NONE")]


def _recording_writer() -> object:
    calls: list[tuple[str, object]] = []
    return types.SimpleNamespace(
        calls=calls,
        setnchannels=lambda value: calls.append(("channels", value)),
        setsampwidth=lambda value: calls.append(("width", value)),
        setframerate=lambda value: calls.append(("rate", value)),
        setcomptype=lambda value, name: calls.append(("compression", value)),
    )


def _reader_with_large_frame_count() -> object:
    return types.SimpleNamespace(
        getnchannels=lambda: 1,
        getsampwidth=lambda: 2,
        getframerate=lambda: 24000,
        getcomptype=lambda: "NONE",
        getcompname=lambda: "not compressed",
        getnframes=lambda: 0xFFFFFFFF,
    )
