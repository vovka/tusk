from abc import ABC, abstractmethod

from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.app_status import AppStatus

__all__ = ["StatusReporter"]


class StatusReporter(ABC):
    @property
    @abstractmethod
    def status(self) -> AppStatus:
        ...

    @abstractmethod
    def set_status(self, status: AppStatus, detail: str = "") -> None:
        ...

    @abstractmethod
    def set_mode(self, mode: AppMode) -> None:
        ...

    @abstractmethod
    def set_models(self, models: tuple[tuple[str, str], ...]) -> None:
        ...

    @abstractmethod
    def set_mic_device(self, device: str) -> None:
        ...
