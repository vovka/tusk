from tusk.lib.agent.agent_run_request import AgentRunRequest
from tusk.lib.agent.agent_session_store import AgentSessionStore

__all__ = ["RuntimeMessageHistoryBuilder"]


class RuntimeMessageHistoryBuilder:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def build(self, session_id: str, request: AgentRunRequest) -> list[dict[str, str]]:
        messages = list(self._store.conversation_messages(session_id))
        return [*messages, *self._ref_messages(request)]

    def _ref_messages(self, request: AgentRunRequest) -> list[dict[str, str]]:
        return [self._ref_message(ref) for ref in request.session_refs]

    def _ref_message(self, ref: str) -> dict[str, str]:
        digest = self._store.session_digest(ref)
        return {"role": "user", "content": f"Referenced session context:\n{digest}"}
