import types

from shells.voice.stages.transcription_buffer import TranscriptionBuffer
from tusk.shared.schemas.utterance import Utterance


def test_buffer_wraps_utterance_in_entry() -> None:
    entry = TranscriptionBuffer(time_source=lambda: 1.0).process(_utterance("open Firefox"))
    assert (entry.id, entry.text, entry.gate_state) == ("u1", "open Firefox", "pending")


def test_buffer_returns_recent_utterances() -> None:
    buffer = TranscriptionBuffer(max_utterances=3)
    for text in ("one", "two", "three", "four"):
        buffer.process(_utterance(text))
    assert [item.text for item in buffer.recent(2)] == ["three", "four"]


def test_buffer_returns_only_recent_dropped_candidates() -> None:
    times = iter([1.0, 50.0, 100.0])
    buffer = TranscriptionBuffer(time_source=lambda: next(times))
    old = buffer.process(_utterance("old"))
    new = buffer.process(_utterance("new"))
    buffer.mark_dropped(old.id)
    buffer.mark_dropped(new.id)
    assert [item.text for item in buffer.recoverable(3, 60.0)] == ["new"]


def test_buffer_logs_full_contents_with_ids_and_states() -> None:
    logs: list[tuple[str, str, str]] = []
    buffer = TranscriptionBuffer(_log(logs), max_utterances=3)
    entry = buffer.process(_utterance("one"))
    buffer.mark_dropped(entry.id)
    assert logs[-1] == ("BUFFER", "size=1\nu1 [dropped]: one", "buffer")


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)


def _log(logs: list[tuple[str, str, str]]) -> object:
    return types.SimpleNamespace(log=lambda *args: logs.append(args))
