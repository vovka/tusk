import io
import types
from contextlib import nullcontext
from unittest.mock import patch

from tusk.providers.tts.wav_concatenator import WavConcatenator


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
