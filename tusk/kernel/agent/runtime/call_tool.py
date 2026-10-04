from tusk.kernel.tools.registered_tool import RegisteredTool
from tusk.shared.schemas.tools.tool_call import ToolCall

__all__ = ["CallTool"]

_NAME = "call_tool"
_PARAMETERS = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "arguments": {"type": "object"}},
    "required": ["name", "arguments"],
}


class CallTool:
    """One generic tool listing every runtime tool as a compact catalogue line instead of a full schema.

    Sending ~30 full schemas per step cost ~2,000 input tokens against Groq's free-tier per-minute cap;
    the catalogue keeps a command step under ~900 tokens.
    """

    @staticmethod
    def definition(tools: list[RegisteredTool]) -> dict[str, object]:
        lines = "\n".join(CallTool._line(tool, CallTool._shown_name(tool, tools)) for tool in tools)
        description = f"Run one desktop tool by name with its arguments. Tools (? = optional):\n{lines}"
        return {"type": "function", "function": {"name": _NAME, "description": description, "parameters": _PARAMETERS}}

    @staticmethod
    def unwrap(tool_call: ToolCall) -> ToolCall:
        # guards, confirmation and the transcript must see the real tool, never the wrapper
        if tool_call.tool_name != _NAME:
            return tool_call
        arguments = tool_call.parameters.get("arguments")
        parameters = arguments if isinstance(arguments, dict) else {}
        return ToolCall(str(tool_call.parameters.get("name", "")), parameters, tool_call.call_id)

    @staticmethod
    def _shown_name(tool: RegisteredTool, tools: list[RegisteredTool]) -> str:
        # the dispatcher resolves a unique short name back to "adapter.name"; the prefix only costs tokens
        short = tool.name.split(".")[-1]
        clashes = [other for other in tools if other.name.split(".")[-1] == short]
        return short if len(clashes) == 1 else tool.name

    @staticmethod
    def _line(tool: RegisteredTool, shown_name: str) -> str:
        schema = tool.input_schema
        required = set(schema.get("required", []))
        fields = [CallTool._field(name, spec, name in required) for name, spec in schema.get("properties", {}).items()]
        return f"{shown_name}({', '.join(fields)}){CallTool._description(tool)}"

    @staticmethod
    def _description(tool: RegisteredTool) -> str:
        # most adapter descriptions only restate the name ("Close a window"); the name alone says it
        words = set(tool.description.lower().split()) - {"a", "an", "the"}
        return "" if words <= set(tool.name.split(".")[-1].split("_")) else f": {tool.description}"

    @staticmethod
    def _field(name: str, spec: dict, required: bool) -> str:
        choices = f"={'|'.join(spec['enum'])}" if "enum" in spec else ""
        return f"{name}{'' if required else '?'}{choices}"
