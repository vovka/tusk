import threading

__all__ = ["InterruptToken"]


class InterruptToken:
    """Shared cooperative-cancellation flag: set on user interrupt, polled at step boundaries."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def interrupt(self) -> None:
        self._event.set()

    @property
    def is_interrupted(self) -> bool:
        return self._event.is_set()

    def clear(self) -> None:
        self._event.clear()
