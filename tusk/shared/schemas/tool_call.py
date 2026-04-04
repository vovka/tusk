from dataclasses import dataclass, field

__all__ = ["ToolCall", "normalize_tool_name"]

_ALIASES = {
    "functions.done": "done",
    "functions.run_agent": "run_agent",
    "functions.execute_tool_sequence": "execute_tool_sequence",
    "finish_agent_run": "done",
    "tool:done": "done",
    "press_keys": "gnome.press_keys",
    "type_text": "gnome.type_text",
    "write_clipboard": "gnome.write_clipboard",
}


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    parameters: dict[str, object] = field(default_factory=dict)
    call_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool_name", normalize_tool_name(self.tool_name))


def normalize_tool_name(name: object) -> str:
    text = str(name or "").strip().strip("[]`")
    if text.startswith("="):
        text = text.lstrip("=")
    if text.startswith("name="):
        text = text.split("=", 1)[1].strip().strip("[]`")
    return _ALIASES.get(text, text)
