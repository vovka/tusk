import threading

__all__ = ["InterruptToken"]


class InterruptToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    @property
    def is_interrupted(self) -> bool:
        return self._event.is_set()

    def interrupt(self) -> None:
        self._event.set()

    def clear(self) -> None:
        self._event.clear()
