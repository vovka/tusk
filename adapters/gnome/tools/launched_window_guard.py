import time
from typing import Callable

__all__ = ["LaunchedWindowGuard"]

# ponytail: "same command" approximated by time; tie to command ids if the adapter ever learns them.
_FRESH_SECONDS = 60.0
_FOCUS_SETTLE_SECONDS = 0.3


class LaunchedWindowGuard:
    """Makes the next typing after an app launch land in the launched window, or explains why it cannot."""

    def __init__(
        self,
        windows: object,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._windows = windows
        self._sleep = sleep
        self._clock = clock
        self._launched: tuple[str, str, float] | None = None

    def remember(self, window_id: str, title: str) -> None:
        self._launched = (window_id, title, self._clock())

    def ensure_active(self) -> str | None:
        launched, self._launched = self._launched, None
        if launched is None or self._clock() - launched[2] > _FRESH_SECONDS:
            return None
        if self._windows.active_window_id() == launched[0]:
            return None
        self._windows.focus(launched[0])
        self._sleep(_FOCUS_SETTLE_SECONDS)
        if self._windows.active_window_id() == launched[0]:
            return None
        return f'not typing: the launched window "{launched[1]}" could not be focused; another window is active'
