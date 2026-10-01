from dataclasses import dataclass

__all__ = ["PendingAction"]


@dataclass(frozen=True)
class PendingAction:
    tool_name: str
    arguments: dict[str, object]
    target_window: str
    follows_active_window: bool
    created_at: float
