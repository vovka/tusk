from shells.voice.stages.transcription_buffer import TranscriptionBuffer
from tusk.shared.schemas.utterance import Utterance


def test_buffer_passes_utterance_through() -> None:
    utterance = _utterance("open Firefox")
    assert TranscriptionBuffer().process(utterance) == utterance


def test_buffer_returns_recent_utterances() -> None:
    buffer = TranscriptionBuffer(max_utterances=3)
    for text in ("one", "two", "three", "four"):
        buffer.process(_utterance(text))
    assert [item.text for item in buffer.recent(2)] == ["three", "four"]


def _utterance(text: str) -> Utterance:
    return Utterance(text, b"", 1.0)
