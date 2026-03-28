import json

from tusk.kernel.schemas.tool_call import ToolCall

__all__ = ["ToolLoopMessageBuilder"]


class ToolLoopMessageBuilder:
    def assistant(self, tool_call: ToolCall) -> dict[str, object]:
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [self._call_payload(tool_call)],
        }

    def tool(self, tool_name: str, call_id: str, content: str) -> dict[str, object]:
        return {"role": "tool", "tool_call_id": call_id, "name": tool_name, "content": content}

    def _call_payload(self, tool_call: ToolCall) -> dict[str, object]:
        return {
            "id": tool_call.call_id or tool_call.tool_name,
            "type": "function",
            "function": self._function(tool_call),
        }

    def _function(self, tool_call: ToolCall) -> dict[str, str]:
        arguments = json.dumps(tool_call.parameters)
        return {"name": tool_call.tool_name, "arguments": arguments}
