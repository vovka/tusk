from abc import ABC, abstractmethod

__all__ = ["Agent"]


class Agent(ABC):
    @abstractmethod
    def process_command(self, command: str) -> str:
        ...
