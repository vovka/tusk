from abc import ABC, abstractmethod

from tusk.schemas.desktop_context import DesktopContext

__all__ = ["ContextProvider"]


class ContextProvider(ABC):
    @abstractmethod
    def get_context(self) -> DesktopContext:
        ...
