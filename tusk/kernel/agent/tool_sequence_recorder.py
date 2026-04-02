from tusk.kernel.agent.agent_session_store import AgentSessionStore
from tusk.shared.schemas.tool_result import ToolResult

__all__ = ["ToolSequenceRecorder"]


class ToolSequenceRecorder:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def started(self, session_id: str, goal: str) -> None:
        self._store.append_event(session_id, "sequence_started", {"goal": goal})

    def requested(self, session_id: str, step_id: str, tool_name: str, args: dict[str, object]) -> None:
        data = {"step_id": step_id, "tool_name": tool_name, "parameters": args}
        self._store.append_event(session_id, "sequence_step_requested", data)

    def result(self, session_id: str, step_id: str, tool_name: str, result: ToolResult) -> None:
        data = {"step_id": step_id, "tool_name": tool_name, "success": result.success, "message": result.message}
        if result.data:
            data["data"] = result.data
        self._store.append_event(session_id, "sequence_step_result", data)

    def finished(self, session_id: str, status: str, summary: str) -> None:
        self._store.append_event(session_id, "sequence_finished", {"status": status, "summary": summary})
