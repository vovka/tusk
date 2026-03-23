from abc import ABC, abstractmethod

__all__ = ["LogPrinter"]


class LogPrinter(ABC):
    @abstractmethod
    def log(self, tag: str, message: str) -> None: ...
