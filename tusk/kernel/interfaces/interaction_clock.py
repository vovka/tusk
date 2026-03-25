from abc import ABC, abstractmethod

__all__ = ["InteractionClock"]


class InteractionClock(ABC):
    @abstractmethod
    def record_interaction(self) -> None:
        ...

    @abstractmethod
    def seconds_since_last_interaction(self) -> float:
        ...

    @abstractmethod
    def is_within_follow_up_window(self) -> bool:
        ...
