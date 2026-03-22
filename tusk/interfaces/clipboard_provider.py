from abc import ABC, abstractmethod

__all__ = ["ClipboardProvider"]


class ClipboardProvider(ABC):
    @abstractmethod
    def read(self) -> str:
        ...

    @abstractmethod
    def write(self, text: str) -> None:
        ...
