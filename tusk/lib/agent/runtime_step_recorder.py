from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.kernel.tool_loop_message_builder import ToolLoopMessageBuilder
from tusk.lib.agent.agent_session_store import AgentSessionStore

__all__ = ["RuntimeStepRecorder"]


class RuntimeStepRecorder:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store
        self._messages = ToolLoopMessageBuilder()

    def append_message(self, session_id: str, role: str, content: str) -> None:
        self._store.append_event(session_id, "message_appended", {"role": role, "content": content})

    def requested(self, session_id: str, step: int, tool_call: ToolCall) -> None:
        data = {"step": step, "tool_name": tool_call.tool_name, "parameters": tool_call.parameters}
        self._store.append_event(session_id, "tool_call_requested", data)

    def appended(self, messages: list[dict[str, object]], tool_call: ToolCall, result: ToolResult) -> None:
        assistant = self._messages.assistant(tool_call)
        tool = self._messages.tool(tool_call.tool_name, tool_call.call_id or tool_call.tool_name, result.message)
        messages.extend([assistant, tool])

    def result(self, session_id: str, step: int, tool_call: ToolCall, result: ToolResult) -> None:
        data = {"step": step, "tool_name": tool_call.tool_name, "success": result.success}
        data.update({"message": result.message, "data": result.data or {}})
        self._store.append_event(session_id, "tool_result_appended", data)
