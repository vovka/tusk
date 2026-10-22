from dataclasses import dataclass

__all__ = ["ModeState"]


@dataclass(frozen=True)
class ModeState:
    adapter_name: str
    session_id: str
    desktop_source: str
