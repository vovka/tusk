from dataclasses import dataclass

__all__ = ["TaskExecutionResult"]


@dataclass(frozen=True)
class TaskExecutionResult:
    status: str
    reply: str
    reason: str = ""
    needed_capability: str = ""
