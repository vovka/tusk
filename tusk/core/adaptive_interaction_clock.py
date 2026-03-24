import time

from tusk.interfaces.interaction_clock import InteractionClock

__all__ = ["AdaptiveInteractionClock"]

_ACTIVITY_WINDOW = 300.0
_LIGHT_THRESHOLD = 1
_MODERATE_THRESHOLD = 3


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
        now = time.monotonic()
        cutoff = now - _ACTIVITY_WINDOW
        recent = sum(1 for t in self._interactions if t > cutoff)
        multiplier = _timeout_multiplier(recent)
        return min(self._base_timeout * multiplier, self._max_timeout)

    def _prune(self, now: float) -> None:
        cutoff = now - _ACTIVITY_WINDOW
        self._interactions = [t for t in self._interactions if t > cutoff]


def _timeout_multiplier(recent_count: int) -> int:
    if recent_count <= _LIGHT_THRESHOLD:
        return 1
    if recent_count <= _MODERATE_THRESHOLD:
        return 2
    return 3
