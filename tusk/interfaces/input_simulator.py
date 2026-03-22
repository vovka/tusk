from abc import ABC, abstractmethod

__all__ = ["InputSimulator"]


class InputSimulator(ABC):
    @abstractmethod
    def press_keys(self, keys: str) -> None:
        ...

    @abstractmethod
    def type_text(self, text: str) -> None:
        ...

    @abstractmethod
    def mouse_click(self, x: int, y: int, button: int, clicks: int) -> None:
        ...

    @abstractmethod
    def mouse_move(self, x: int, y: int) -> None:
        ...

    @abstractmethod
    def mouse_drag(self, from_x: int, from_y: int, to_x: int, to_y: int, button: int) -> None:
        ...

    @abstractmethod
    def mouse_scroll(self, direction: str, clicks: int) -> None:
        ...
