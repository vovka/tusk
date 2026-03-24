import time

from tusk.interfaces.interaction_clock import InteractionClock

__all__ = ["MonotonicInteractionClock"]


class MonotonicInteractionClock(InteractionClock):
    def __init__(self, follow_up_timeout_seconds: float) -> None:
        self._timeout = follow_up_timeout_seconds
        self._last_interaction: float | None = None

    def record_interaction(self) -> None:
        self._last_interaction = time.monotonic()

    def seconds_since_last_interaction(self) -> float:
        if self._last_interaction is None:
            return float("inf")
        return time.monotonic() - self._last_interaction

    def is_within_follow_up_window(self) -> bool:
        return self.seconds_since_last_interaction() < self._timeout
