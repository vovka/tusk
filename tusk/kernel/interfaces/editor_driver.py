from abc import ABC, abstractmethod

from tusk.shared.schemas.buffer_selection import BufferSelection

__all__ = ["EditorDriver"]


class EditorDriver(ABC):
    @abstractmethod
    def read_buffer(self) -> str: ...

    @abstractmethod
    def goto_line(self, line_number: int) -> None: ...

    @abstractmethod
    def select_range(self, selection: BufferSelection) -> None: ...

    @abstractmethod
    def paste(self, text: str) -> None: ...

    @abstractmethod
    def type_text(self, text: str) -> None: ...

    @abstractmethod
    def press_keys(self, keys: str) -> None: ...

    @abstractmethod
    def replace_buffer(self, text: str) -> None: ...
