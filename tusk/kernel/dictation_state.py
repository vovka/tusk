from dataclasses import dataclass

__all__ = ["DictationState"]


@dataclass(frozen=True)
class DictationState:
    adapter_name: str
    session_id: str
    desktop_source: str
