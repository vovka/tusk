from abc import ABC, abstractmethod

from shells.tray.tray_menu_item import TrayMenuItem

__all__ = ["TrayBackend"]


class TrayBackend(ABC):
    @abstractmethod
    def run(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def set_icon(self, name: str) -> None:
        ...

    @abstractmethod
    def set_tooltip(self, text: str) -> None:
        ...

    @abstractmethod
    def set_menu(self, items: tuple[TrayMenuItem, ...]) -> None:
        ...
