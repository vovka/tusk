from tusk.kernel.agent_backends.agent_backend import AgentBackend
from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.agent_result import AgentResult
from tusk.kernel.interfaces.agent import Agent

__all__ = ["TuskAgentBackend"]


class TuskAgentBackend(AgentBackend):
    def __init__(self, agent: Agent) -> None:
        if agent is None:
            raise ValueError("agent cannot be None")
        self._agent = agent

    @property
    def name(self) -> str:
        return "tusk"

    @property
    def supports_streaming(self) -> bool:
        return False

    def run(self, request: AgentRequest) -> AgentResult:
        if request is None:
            raise ValueError("request cannot be None")
        reply = self._agent.process_command(request.user_text)
        metadata = {**request.metadata, "backend": self.name, "mode": request.mode}
        return AgentResult(True, reply, request.session_id, metadata)
