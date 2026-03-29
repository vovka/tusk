from tusk.lib.agent.agent_run_request import AgentRunRequest
from tusk.lib.agent.agent_session_store import AgentSessionStore

__all__ = ["RuntimeMessageHistoryBuilder"]


class RuntimeMessageHistoryBuilder:
    def __init__(self, session_store: AgentSessionStore) -> None:
        self._store = session_store

    def build(self, session_id: str, request: AgentRunRequest) -> list[dict[str, str]]:
        messages = self._prior_messages(session_id)
        self._append_session_refs(messages, request.session_refs)
        return messages

    def _prior_messages(self, session_id: str) -> list[dict[str, str]]:
        return list(self._store.conversation_messages(session_id))

    def _append_session_refs(self, messages: list[dict[str, str]], refs: tuple[str, ...]) -> None:
        for ref in refs:
            digest = self._store.session_digest(ref)
            if digest:
                messages.append({"role": "user", "content": f"[session-ref] {digest}"})
