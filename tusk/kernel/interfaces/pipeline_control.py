from abc import ABC, abstractmethod

__all__ = ["PipelineControl"]


class PipelineControl(ABC):
    @abstractmethod
    def pause(self) -> None:
        ...

    @abstractmethod
    def resume(self) -> None:
        ...
