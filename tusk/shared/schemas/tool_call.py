from dataclasses import dataclass, field

__all__ = ["ToolCall"]


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    parameters: dict[str, object] = field(default_factory=dict)
    call_id: str = ""
