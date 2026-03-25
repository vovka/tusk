from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_loop_message_builder import ToolLoopMessageBuilder

__all__ = ["ToolLoopRecorder"]


class ToolLoopRecorder:
    def __init__(self, log_printer: LogPrinter) -> None:
        self._log = log_printer
        self._builder = ToolLoopMessageBuilder()

    def remember_tool_call(self, messages: list[dict[str, str]], tool_call: ToolCall, label: str) -> None:
        detail = f"{tool_call.tool_name} {tool_call.parameters!r}"
        self._log.log("LLM", f"[{label}] agent tool → {detail}")
        messages.append(self._builder.assistant(tool_call))

    def add_feedback(self, messages: list[dict[str, str]], name: str, result: ToolResult) -> None:
        self._log.log("TOOL", result.message)
        messages.append(self._builder.tool(name, self._call_id(name, messages), result.message))

    def _call_id(self, name: str, messages: list[dict[str, str]]) -> str:
        for message in reversed(messages):
            if message.get("role") != "assistant":
                continue
            for call in message.get("tool_calls", []):
                if call["function"]["name"] == name:
                    return str(call["id"])
        return name
