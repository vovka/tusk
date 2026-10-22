import time
from collections import deque

from tusk.shared.schemas.voice.buffered_utterance import BufferedUtterance
from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.voice.utterance import Utterance

__all__ = ["TranscriptionBuffer"]


class TranscriptionBuffer:
    def __init__(
        self,
        log_printer: LogPrinter | None = None,
        max_utterances: int = 50,
        time_source: object = time.monotonic,
    ) -> None:
        self._utterances: deque[BufferedUtterance] = deque(maxlen=max_utterances)
        self._log = log_printer
        self._time = time_source
        self._next_id = 0

    def process(self, utterance: Utterance) -> BufferedUtterance:
        entry = BufferedUtterance(self._new_id(), utterance, self._time())
        self._utterances.append(entry)
        self._log_state()
        return entry

    def recent(self, count: int) -> list[Utterance]:
        return [item.utterance for item in list(self._utterances)[-count:]]

    def recoverable(self, count: int, max_age_seconds: float) -> list[BufferedUtterance]:
        if count <= 0 or max_age_seconds <= 0:
            return []
        cutoff = self._time() - max_age_seconds
        items = [item for item in self._utterances if _is_recoverable(item, cutoff)]
        return items[-count:]

    def mark_dropped(self, entry_id: str) -> None:
        self._set_dropped(entry_id, True)

    def mark_recovered(self, entry_id: str) -> None:
        self._set_dropped(entry_id, False)

    def _set_dropped(self, entry_id: str, dropped: bool) -> None:
        entry = self._entry(entry_id)
        if entry is None:
            return
        entry.dropped = dropped
        self._log_state()

    def _entry(self, entry_id: str) -> BufferedUtterance | None:
        return next((item for item in self._utterances if item.id == entry_id), None)

    def _log_state(self) -> None:
        if self._log is not None:
            self._log.log("BUFFER", self._message(), "buffer")

    def _message(self) -> str:
        lines = [f"{item.id}{' [dropped]' if item.dropped else ''}: {item.text}" for item in self._utterances]
        return "\n".join([f"size={len(self._utterances)}", *lines])

    def _new_id(self) -> str:
        self._next_id += 1
        return f"u{self._next_id}"


def _is_recoverable(item: BufferedUtterance, cutoff: float) -> bool:
    return item.dropped and item.received_at >= cutoff
