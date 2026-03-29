from tusk.lib.agent.agent_result import AgentResult
from tusk.lib.agent.agent_session_store import AgentSessionStore

__all__ = ["RuntimeResultFactory"]


class RuntimeResultFactory:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def from_parameters(self, session_id: str, parameters: dict[str, object]) -> AgentResult:
        params = self._normalized(parameters)
        return AgentResult(
            str(params.get("status", "done")),
            session_id,
            str(params.get("summary", "")),
            str(params.get("text", "")),
            dict(params.get("payload", {})),
            list(params.get("artifact_refs", [])),
        )

    def failed(self, session_id: str, reason: str) -> AgentResult:
        return AgentResult("failed", session_id, reason, reason)

    def persist(self, session_id: str, result: AgentResult, reply: str) -> AgentResult:
        self._store.append_event(session_id, "message_appended", {"role": "assistant", "content": reply})
        self._store.append_event(session_id, "session_finished", result.to_dict())
        return result

    def _normalized(self, parameters: dict[str, object]) -> dict[str, object]:
        reply = str(parameters.get("reply", ""))
        if reply and "summary" not in parameters and "text" not in parameters:
            return {"status": "done", "summary": reply, "text": reply}
        return parameters
