import json

from tusk.kernel.schemas.tool_call import ToolCall

__all__ = ["RepeatedToolCallGuard"]


class RepeatedToolCallGuard:
    def __init__(self) -> None:
        self._last = ""
        self._count = 0

    def repeated(self, tool_call: ToolCall) -> bool:
        signature = self._signature(tool_call)
        self._count = self._count + 1 if signature == self._last else 1
        self._last = signature
        return self._count >= 3

    def _signature(self, tool_call: ToolCall) -> str:
        payload = {"tool": tool_call.tool_name, "arguments": tool_call.parameters}
        return json.dumps(payload, sort_keys=True, default=str)
