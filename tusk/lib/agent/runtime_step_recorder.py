from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.lib.agent.agent_session_store import AgentSessionStore

__all__ = ["RuntimeStepRecorder"]


class RuntimeStepRecorder:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def append_message(self, session_id: str, role: str, content: str) -> None:
        self._store.append_event(session_id, "message_appended", {"role": role, "content": content})

    def requested(self, session_id: str, step: int, tool_call: ToolCall) -> None:
        data = {"step": step, "tool_name": tool_call.tool_name, "parameters": tool_call.parameters}
        self._store.append_event(session_id, "tool_call_requested", data)

    def result(self, session_id: str, step: int, tool_call: ToolCall, tool_result: ToolResult) -> None:
        data = {"step": step, "tool_name": tool_call.tool_name, "success": tool_result.success, "message": tool_result.message}
        self._store.append_event(session_id, "tool_call_result", data)

    def appended(self, messages: list[dict[str, str]], tool_call: ToolCall, tool_result: ToolResult) -> None:
        messages.append({"role": "assistant", "content": f"[tool:{tool_call.tool_name}] called"})
        messages.append({"role": "user", "content": tool_result.message})
