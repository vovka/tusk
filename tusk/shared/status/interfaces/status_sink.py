from abc import ABC, abstractmethod

from tusk.shared.schemas.status_snapshot import StatusSnapshot

__all__ = ["StatusSink"]


class StatusSink(ABC):
    @abstractmethod
    def publish(self, snapshot: StatusSnapshot) -> None:
        ...
