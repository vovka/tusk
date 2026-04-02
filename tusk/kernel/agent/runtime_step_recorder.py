from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult
from tusk.kernel.agent.child_result_message_builder import ChildResultMessageBuilder
from tusk.kernel.agent.clipboard_write_message_builder import ClipboardWriteMessageBuilder
from tusk.kernel.agent.agent_session_store import AgentSessionStore

__all__ = ["RuntimeStepRecorder"]


class RuntimeStepRecorder:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store
        self._children = ChildResultMessageBuilder()
        self._clipboard = ClipboardWriteMessageBuilder()

    def append_message(self, session_id: str, role: str, content: str) -> None:
        self._store.append_event(session_id, "message_appended", {"role": role, "content": content})

    def requested(self, session_id: str, step: int, tool_call: ToolCall) -> None:
        data = {"step": step, "tool_name": tool_call.tool_name, "parameters": tool_call.parameters}
        self._store.append_event(session_id, "tool_call_requested", data)

    def result(self, session_id: str, step: int, tool_call: ToolCall, tool_result: ToolResult) -> None:
        data = {"step": step, "tool_name": tool_call.tool_name, "success": tool_result.success, "message": tool_result.message}
        if tool_result.data:
            data["data"] = tool_result.data
        self._store.append_event(session_id, "tool_call_result", data)

    def appended(self, messages: list[dict[str, str]], tool_call: ToolCall, tool_result: ToolResult) -> None:
        messages.append({"role": "assistant", "content": f"[tool:{tool_call.tool_name}] called"})
        child = self._children.build(tool_result)
        if child is not None:
            messages.append({"role": "assistant", "content": child})
            return
        messages.append({"role": "user", "content": tool_result.message})
        clipboard = self._clipboard.build(tool_call, tool_result)
        if clipboard is not None:
            messages.append({"role": "assistant", "content": clipboard})
