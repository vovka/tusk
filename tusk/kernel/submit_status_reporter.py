from collections.abc import Callable
from threading import Lock

from tusk.shared.schemas.app_status import AppStatus

__all__ = ["SubmitStatusReporter"]


class SubmitStatusReporter:
    """Wraps a submit call with REACTING status, restoring the prior status once all
    concurrent submits finish."""

    def __init__(self, reporter: object) -> None:
        self._reporter = reporter
        self._lock = Lock()
        self._active = 0
        self._restore = AppStatus.LISTENING

    def run(self, text: str, route: Callable[[str], object]) -> object:
        self._begin(text)
        try:
            return route(text)
        finally:
            self._end()

    def _begin(self, text: str) -> None:
        with self._lock:
            if self._active == 0:
                self._restore = self._reporter.status
            self._active += 1
            self._reporter.set_status(AppStatus.REACTING, text)

    def _end(self) -> None:
        with self._lock:
            self._active -= 1
            if self._active == 0:
                self._reporter.set_status(self._restore)
