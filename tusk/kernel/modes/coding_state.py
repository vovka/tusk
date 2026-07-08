from dataclasses import dataclass

__all__ = ["CodingState"]


@dataclass(frozen=True)
class CodingState:
    adapter_name: str
    session_id: str
    desktop_source: str
