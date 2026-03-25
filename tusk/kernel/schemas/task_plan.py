from dataclasses import dataclass, field

__all__ = ["TaskPlan"]


@dataclass(frozen=True)
class TaskPlan:
    status: str
    user_reply: str
    plan_steps: list[str] = field(default_factory=list)
    selected_tools: list[str] = field(default_factory=list)
    reason: str = ""
