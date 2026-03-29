from abc import ABC, abstractmethod

from tusk.lib.agent.agent_result import AgentResult

__all__ = ["AgentSessionStore"]


class AgentSessionStore(ABC):
    @abstractmethod
    def create_session_id(self) -> str: ...

    @abstractmethod
    def has_session(self, session_id: str) -> bool: ...

    @abstractmethod
    def start_session(
        self,
        session_id: str,
        profile_id: str,
        parent_session_id: str,
        parent_call_id: str,
        metadata: dict[str, object],
    ) -> None: ...

    @abstractmethod
    def append_event(self, session_id: str, event_type: str, data: dict[str, object]) -> None: ...

    @abstractmethod
    def conversation_messages(self, session_id: str) -> list[dict[str, str]]: ...

    @abstractmethod
    def session_digest(self, session_id: str) -> str: ...

    @abstractmethod
    def final_result(self, session_id: str) -> AgentResult | None: ...
