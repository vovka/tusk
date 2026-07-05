import queue
from collections.abc import Iterator

from tusk.shared.schemas.utterance import Utterance

__all__ = ["QueueDetector"]


class QueueDetector:
    """Stands in for mic + VAD: the harness scripts what TUSK 'hears'."""

    def __init__(self) -> None:
        self._queue: "queue.Queue[Utterance | None]" = queue.Queue()

    def say(self, text: str, duration_seconds: float = 2.0) -> None:
        self._queue.put(Utterance(text, b"e2e-audio", duration_seconds))

    def close(self) -> None:
        self._queue.put(None)

    def stream_utterances(self) -> Iterator[Utterance]:
        while (item := self._queue.get()) is not None:
            yield item
