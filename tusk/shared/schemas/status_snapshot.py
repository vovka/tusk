from dataclasses import dataclass

from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.app_status import AppStatus

__all__ = ["StatusSnapshot"]


@dataclass(frozen=True)
class StatusSnapshot:
    status: AppStatus
    mode: AppMode
    detail: str = ""
    mic_device: str = ""
    models: tuple[tuple[str, str], ...] = ()
