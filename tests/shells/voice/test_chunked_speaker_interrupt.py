import threading
import types

from shells.voice.stages.chunked_speaker import ChunkedSpeaker


def _interrupt_engine(gate: threading.Event, pulled: list[str]) -> object:
    def synthesize_chunks(text: str):
        yield b"one"
        pulled.append("two")
        yield b"two"
        assert gate.wait(timeout=5.0)
        pulled.append("three")
        yield b"three"

    return types.SimpleNamespace(synthesize_chunks=synthesize_chunks)


def _interrupting_playback(played: list[bytes], token: object) -> object:
    def play(wav_clip: bytes) -> None:
        played.append(wav_clip)
        token.is_interrupted = True

    return types.SimpleNamespace(play=play)


def test_no_playback_when_interrupt_already_pending() -> None:
    token = types.SimpleNamespace(is_interrupted=True)
    played: list[bytes] = []
    engine = types.SimpleNamespace(synthesize_chunks=lambda text: iter([b"one", b"two"]))
    log = types.SimpleNamespace(log=lambda *args: None)
    ChunkedSpeaker(engine, types.SimpleNamespace(play=played.append), log, token).speak("hi")
    assert played == []


def test_interrupt_stops_playback_and_further_synthesis() -> None:
    token = types.SimpleNamespace(is_interrupted=False)
    played: list[bytes] = []
    pulled: list[str] = []
    gate = threading.Event()
    log = types.SimpleNamespace(log=lambda *args: None)
    speaker = ChunkedSpeaker(_interrupt_engine(gate, pulled), _interrupting_playback(played, token), log, token)
    speaker.speak("hi")
    gate.set()
    assert played == [b"one"]
    assert "three" not in pulled
