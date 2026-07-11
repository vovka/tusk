from abc import ABC, abstractmethod
from collections.abc import Iterator

__all__ = ["TTSEngine"]


class TTSEngine(ABC):
    @abstractmethod
    def synthesize_chunks(self, text: str) -> Iterator[bytes]:
        ...
