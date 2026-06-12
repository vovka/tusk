from abc import ABC, abstractmethod

__all__ = ["TTSEngine"]


class TTSEngine(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        ...
