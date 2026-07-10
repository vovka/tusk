import threading
import types

from shells.voice.stages.chunked_speaker import ChunkedSpeaker
from tests.command_worker_support import await_condition


def _speaker(engine: object | None, played: list[bytes], on_play: object | None = None) -> ChunkedSpeaker:
    def play(wav_clip: bytes) -> None:
        played.append(wav_clip)
        if on_play is not None:
            on_play()
    log = types.SimpleNamespace(log=lambda *args: None)
    return ChunkedSpeaker(engine, types.SimpleNamespace(play=play), log)


def test_plays_one_clip_per_chunk_in_order() -> None:
    played: list[bytes] = []
    engine = types.SimpleNamespace(synthesize_chunks=lambda text: iter([b"one", b"two"]))
    _speaker(engine, played).speak("hello world")
    assert played == [b"one", b"two"]


def _gated_engine(release: threading.Event) -> object:
    def synthesize_chunks(text: str):
        yield b"one"
        assert release.wait(timeout=5.0)
        yield b"two"

    return types.SimpleNamespace(synthesize_chunks=synthesize_chunks)


def _failing_engine() -> object:
    def synthesize_chunks(text: str):
        yield b"one"
        raise RuntimeError("tts unavailable")

    return types.SimpleNamespace(synthesize_chunks=synthesize_chunks)


def test_first_clip_plays_before_later_chunks_are_synthesized() -> None:
    played: list[bytes] = []
    release = threading.Event()
    _speaker(_gated_engine(release), played, on_play=release.set).speak("hi")
    assert played == [b"one", b"two"]


def test_synthesis_failure_is_logged_and_playback_stops() -> None:
    logs: list[tuple] = []
    played: list[bytes] = []
    log = types.SimpleNamespace(log=lambda *args: logs.append(args))
    playback = types.SimpleNamespace(play=lambda wav_clip: played.append(wav_clip))
    ChunkedSpeaker(_failing_engine(), playback, log).speak("hi")
    assert played == [b"one"]
    assert any(entry[0] == "ERROR" for entry in logs)


def test_current_text_set_only_while_speaking() -> None:
    seen: list[str | None] = []
    engine = types.SimpleNamespace(synthesize_chunks=lambda text: iter([b"one"]))
    played: list[bytes] = []
    speaker = _speaker(engine, played, on_play=lambda: seen.append(speaker.current_text))
    speaker.speak("hello")
    assert seen == ["hello"]
    await_condition(lambda: speaker.current_text is None)


def test_speak_without_engine_does_nothing() -> None:
    played: list[bytes] = []
    _speaker(None, played).speak("hello")
    assert played == []
