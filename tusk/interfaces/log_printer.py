from abc import ABC, abstractmethod

__all__ = ["LogPrinter"]


class LogPrinter(ABC):
    @abstractmethod
    def log(self, tag: str, message: str) -> None: ...

    @abstractmethod
    def show_wait(self, label: str) -> None: ...

    @abstractmethod
    def clear_wait(self) -> None: ...
