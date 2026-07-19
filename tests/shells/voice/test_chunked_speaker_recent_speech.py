import types

from shells.voice.stages import chunked_speaker
from shells.voice.stages.chunked_speaker import ChunkedSpeaker


def _two_chunk_speaker(played: list[bytes]) -> ChunkedSpeaker:
    engine = types.SimpleNamespace(synthesize_chunks=lambda text: iter([b"one", b"two"]))
    log = types.SimpleNamespace(log=lambda *args: None)
    return ChunkedSpeaker(engine, types.SimpleNamespace(play=played.append), log)


def test_recent_speech_keeps_latest_timestamp_across_chunks(monkeypatch) -> None:
    speaker = _two_chunk_speaker([])
    clip_times = iter([10.0, 20.0])
    monkeypatch.setattr(chunked_speaker.time, "monotonic", lambda: next(clip_times))
    speaker.speak("Opening gedit with a poem.")
    assert speaker.recent_speech() == [("Opening gedit with a poem.", 20.0)]
