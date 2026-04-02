from dataclasses import dataclass

__all__ = ["ToolSequenceStep"]


@dataclass(frozen=True)
class ToolSequenceStep:
    step_id: str
    tool_name: str
    args: dict[str, object]

    @classmethod
    def from_dict(cls, data: object) -> "ToolSequenceStep | None":
        if not isinstance(data, dict) or not isinstance(data.get("args"), dict):
            return None
        return cls(str(data.get("id", "")), str(data.get("tool_name", "")), dict(data["args"]))

    def to_dict(self) -> dict[str, object]:
        return {"id": self.step_id, "tool_name": self.tool_name, "args": dict(self.args)}
