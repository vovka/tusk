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

    def model_failure_text(self, exc: Exception) -> str:
        text = str(exc).lower()
        if "rate limit" in text or "429" in text:
            return "The model is currently rate limited. Please try again in a few minutes."
        if "json_validate_failed" in text:
            return "I couldn't build a reliable plan for that request. Please try again."
        if "tool_use_failed" in text:
            return "The model returned an invalid tool call. Please try again."
        if "empty completion" in text:
            return "The model returned an empty response. Please try again."
        return "The model is temporarily unavailable. Please try again."

    def persist(self, session_id: str, result: AgentResult, reply: str) -> AgentResult:
        self._store.append_event(session_id, "session_finished", result.to_dict())
        self._store.append_event(session_id, "message_appended", {"role": "assistant", "content": reply})
        return result


def _payload(status: str, parameters: dict[str, object]) -> dict[str, object]:
    payload = dict(parameters.get("payload", {}))
    # the agent wrote this failure as a spoken sentence (e.g. a tool's "unknown model" answer), unlike runtime guards
    return {**payload, "agent_authored": True} if status == "failed" else payload
