from dataclasses import replace

from tusk.shared.schemas.tools.tool_call import ToolCall

__all__ = ["ToolNameNormalizer"]

# names models emit for the static tools, plus adapter tools they call without the prefix
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


class ToolNameNormalizer:
    @staticmethod
    def tool_call(tool_call: ToolCall) -> ToolCall:
        return replace(tool_call, tool_name=ToolNameNormalizer.name(tool_call.tool_name))

    @staticmethod
    def name(raw: object) -> str:
        text = str(raw or "").strip().strip("[]`")
        if text.startswith("="):
            text = text.lstrip("=")
        if text.startswith("name="):
            text = text.split("=", 1)[1].strip().strip("[]`")
        return _ALIASES.get(text, text)
