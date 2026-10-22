from abc import ABC, abstractmethod

__all__ = ["LogPrinter"]


class LogPrinter(ABC):
    @abstractmethod
    def log(self, tag: str, message: str, group: str | None = None) -> None: ...

    @abstractmethod
    def show_wait(self, label: str, group: str = "wait") -> None: ...

    @abstractmethod
    def clear_wait(self) -> None: ...
