from dataclasses import dataclass

__all__ = ["ToolUsageStats"]


@dataclass(frozen=True)
class ToolUsageStats:
    score: float
    count: int
    last_used_at: float
