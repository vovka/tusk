from abc import ABC, abstractmethod

__all__ = ["Shell"]


class Shell(ABC):
    @abstractmethod
    def start(self, api: object) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...
