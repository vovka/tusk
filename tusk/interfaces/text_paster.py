from abc import ABC, abstractmethod

__all__ = ["TextPaster"]


class TextPaster(ABC):
    @abstractmethod
    def paste(self, text: str) -> None:
        ...

    @abstractmethod
    def replace(self, char_count: int, new_text: str) -> None:
        ...
