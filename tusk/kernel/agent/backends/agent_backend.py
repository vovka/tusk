from abc import ABC, abstractmethod

from tusk.kernel.agent.backends.backend_request import BackendRequest
from tusk.kernel.agent.backends.backend_result import BackendResult

__all__ = ["AgentBackend"]


class AgentBackend(ABC):
    @abstractmethod
    def run(self, request: BackendRequest) -> BackendResult:
        ...
