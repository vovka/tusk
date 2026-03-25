import time

from tusk.kernel.interfaces.interaction_clock import InteractionClock

__all__ = ["AdaptiveInteractionClock"]

_ACTIVITY_WINDOW = 300.0


class AdaptiveInteractionClock(InteractionClock):
    def __init__(self, base_timeout: float, max_timeout: float) -> None:
        self._base_timeout = base_timeout
        self._max_timeout = max_timeout
        self._interactions: list[float] = []

    def record_interaction(self) -> None:
        now = time.monotonic()
        self._interactions.append(now)
        self._prune(now)

    def seconds_since_last_interaction(self) -> float:
        if not self._interactions:
            return float("inf")
        return time.monotonic() - self._interactions[-1]

    def is_within_follow_up_window(self) -> bool:
        return self.seconds_since_last_interaction() < self._effective_timeout()

    def _effective_timeout(self) -> float:
        cutoff = time.monotonic() - _ACTIVITY_WINDOW
        recent = sum(1 for item in self._interactions if item > cutoff)
        multiplier = 1 if recent <= 1 else 2 if recent <= 3 else 3
        return min(self._base_timeout * multiplier, self._max_timeout)

    def _prune(self, now: float) -> None:
        cutoff = now - _ACTIVITY_WINDOW
        self._interactions = [item for item in self._interactions if item > cutoff]
