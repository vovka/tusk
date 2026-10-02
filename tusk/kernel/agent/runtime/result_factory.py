from tusk.kernel.agent.agent_result import AgentResult
from tusk.kernel.agent.session.store import Store

__all__ = ["ResultFactory"]


class ResultFactory:
    def __init__(self, session_store: Store) -> None:
        self._store = session_store

    def from_parameters(self, session_id: str, parameters: dict[str, object]) -> AgentResult:
        status = str(parameters.get("status", "done"))
        return AgentResult(
            status=status,
            session_id=session_id,
            summary=str(parameters.get("summary", "")),
            text=str(parameters.get("text", parameters.get("reply", ""))),
            payload=_payload(status, parameters),
            artifact_refs=list(parameters.get("artifact_refs", [])),
        )

    def failed(self, session_id: str, reason: str) -> AgentResult:
        return AgentResult("failed", session_id, reason, reason)

    def cancelled(self, session_id: str) -> AgentResult:
        return AgentResult("cancelled", session_id, "cancelled by user")

    def persist(self, session_id: str, result: AgentResult, reply: str) -> AgentResult:
        self._store.append_event(session_id, "session_finished", result.to_dict())
        self._store.append_event(session_id, "message_appended", {"role": "assistant", "content": reply})
        return result


def _payload(status: str, parameters: dict[str, object]) -> dict[str, object]:
    payload = dict(parameters.get("payload", {}))
    # the agent wrote this failure as a spoken sentence (e.g. a tool's "unknown model" answer), unlike runtime guards
    return {**payload, "agent_authored": True} if status == "failed" else payload
