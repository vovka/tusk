from dataclasses import dataclass

__all__ = ["QueuedCommand"]


@dataclass(frozen=True)
class QueuedCommand:
    text: str
    clear_before_run: bool = False
