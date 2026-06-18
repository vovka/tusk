from abc import ABC, abstractmethod

from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.agent_result import AgentResult

__all__ = ["AgentBackend"]


class AgentBackend(ABC):
    @abstractmethod
    def run(self, request: AgentRequest) -> AgentResult:
        ...
