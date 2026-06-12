import time
from collections.abc import Callable

__all__ = ["DictationSessionStore"]


class DictationSessionStore:
    def __init__(self, time_source: Callable[[], float] = time.monotonic, max_age_seconds: float = 3600.0) -> None:
        self._time = time_source
        self._max_age = max_age_seconds
        self._entries: dict[str, tuple[str, float]] = {}

    def __contains__(self, session_id: str) -> bool:
        return session_id in self._entries

    def get(self, session_id: str) -> str:
        return self._entries.get(session_id, ("", 0.0))[0]

    def set(self, session_id: str, text: str) -> None:
        self._entries[session_id] = (text, self._time())

    def pop(self, session_id: str) -> None:
        self._entries.pop(session_id, None)

    def prune_stale(self) -> None:
        now = self._time()
        stale = [key for key, (_, used_at) in self._entries.items() if now - used_at > self._max_age]
        for key in stale:
            self._entries.pop(key)
