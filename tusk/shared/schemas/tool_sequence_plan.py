from dataclasses import dataclass

from tusk.shared.schemas.tool_sequence_step import ToolSequenceStep

__all__ = ["ToolSequencePlan"]


@dataclass(frozen=True)
class ToolSequencePlan:
    steps: tuple[ToolSequenceStep, ...]
    goal: str = ""

    @classmethod
    def from_dict(cls, data: object) -> "ToolSequencePlan | None":
        if not isinstance(data, dict) or not isinstance(data.get("steps"), list):
            return None
        steps = tuple(ToolSequenceStep.from_dict(item) for item in data["steps"])
        if any(step is None for step in steps):
            return None
        return cls(tuple(step for step in steps if step is not None), str(data.get("goal", "")))

    def to_dict(self) -> dict[str, object]:
        return {"goal": self.goal, "steps": [step.to_dict() for step in self.steps]}

    def tool_names(self) -> set[str]:
        return {step.tool_name for step in self.steps}

    def ordered_tool_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(step.tool_name for step in self.steps))
