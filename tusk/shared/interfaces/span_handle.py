from abc import ABC, abstractmethod

__all__ = ["SpanHandle"]


class SpanHandle(ABC):
    @abstractmethod
    def set_attribute(self, key: str, value: str) -> None:
        ...
