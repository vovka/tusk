from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.agent_session_store import AgentSessionStore

__all__ = ["RuntimeResultFactory"]


class RuntimeResultFactory:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def from_parameters(self, session_id: str, parameters: dict[str, object]) -> AgentResult:
        return AgentResult(
            status=str(parameters.get("status", "done")),
            session_id=session_id,
            summary=str(parameters.get("summary", "")),
            text=str(parameters.get("text", parameters.get("reply", ""))),
            payload=dict(parameters.get("payload", {})),
            artifact_refs=list(parameters.get("artifact_refs", [])),
        )

    def failed(self, session_id: str, reason: str) -> AgentResult:
        return AgentResult("failed", session_id, reason, reason)

    def persist(self, session_id: str, result: AgentResult, reply: str) -> AgentResult:
        self._store.append_event(session_id, "session_finished", result.to_dict())
        self._store.append_event(session_id, "message_appended", {"role": "assistant", "content": reply})
        return result
