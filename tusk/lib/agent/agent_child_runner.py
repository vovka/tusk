from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.lib.agent.agent_result import AgentResult
from tusk.lib.agent.agent_run_request import AgentRunRequest
from tusk.lib.agent.agent_session_store import AgentSessionStore

__all__ = ["AgentChildRunner"]


class AgentChildRunner:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def request(self, tool_call: ToolCall, parent_session_id: str) -> AgentRunRequest:
        params = tool_call.parameters
        return AgentRunRequest(
            instruction=str(params.get("instruction", "")),
            profile_id=str(params.get("profile_id", "default")),
            parent_session_id=parent_session_id,
            parent_call_id=tool_call.call_id,
            runtime_tool_names=tuple(params.get("runtime_tool_names", ())),
            session_refs=tuple(params.get("session_refs", ())),
        )

    def invalid_request(self) -> ToolResult:
        return ToolResult(False, "run_agent requires an instruction")

    def started(self, parent_session_id: str, child: AgentRunRequest) -> None:
        data = {"child_profile": child.profile_id, "child_instruction": child.instruction[:120]}
        self._store.append_event(parent_session_id, "child_started", data)

    def finished(self, parent_session_id: str, profile_id: str, result: AgentResult) -> None:
        data = {"child_profile": profile_id, "child_session": result.session_id, "child_status": result.status}
        self._store.append_event(parent_session_id, "child_finished", data)

    def result(self, profile_id: str, agent_result: AgentResult) -> ToolResult:
        data = {"child_result": {"profile_id": profile_id, **agent_result.to_dict()}}
        return ToolResult(agent_result.status == "done", agent_result.reply_text(), data)
