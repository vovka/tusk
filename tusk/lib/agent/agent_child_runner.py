import json

from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.schemas.tool_result import ToolResult
from tusk.lib.agent.agent_result import AgentResult
from tusk.lib.agent.agent_run_request import AgentRunRequest
from tusk.lib.agent.agent_session_store import AgentSessionStore

__all__ = ["AgentChildRunner"]


class AgentChildRunner:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def request(self, tool_call: ToolCall, session_id: str) -> AgentRunRequest:
        params = tool_call.parameters
        return AgentRunRequest(
            str(params.get("instruction", "")),
            str(params.get("profile_id", "default") or "default"),
            "",
            session_id,
            tool_call.call_id or tool_call.tool_name,
            tuple(str(item) for item in params.get("runtime_tool_names", [])),
            tuple(str(item) for item in params.get("session_refs", [])),
            {},
        )

    def invalid_request(self) -> ToolResult:
        data = {"status": "failed", "summary": "run_agent requires instruction"}
        return ToolResult(False, json.dumps(data))

    def started(self, session_id: str, child: AgentRunRequest) -> None:
        self._store.append_event(session_id, "child_session_started", _child_data(child))

    def finished(self, session_id: str, result: AgentResult) -> None:
        self._store.append_event(session_id, "child_session_finished", result.to_dict())

    def result(self, result: AgentResult) -> ToolResult:
        payload = result.to_dict()
        return ToolResult(result.status != "failed", json.dumps(payload), payload)


def _child_data(child: AgentRunRequest) -> dict[str, object]:
    return {"profile_id": child.profile_id, "instruction": child.instruction}
