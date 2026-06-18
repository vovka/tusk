from tusk.kernel.agent_backends.agent_backend import AgentBackend
from tusk.kernel.agent_backends.agent_request import AgentRequest
from tusk.kernel.agent_backends.agent_result import AgentResult
from tusk.kernel.interfaces.agent import Agent

__all__ = ["TuskAgentBackend"]


class TuskAgentBackend(AgentBackend):
    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    @property
    def name(self) -> str:
        return "tusk"

    @property
    def supports_streaming(self) -> bool:
        return False

    def run(self, request: AgentRequest) -> AgentResult:
        reply = self._agent.process_command(request.user_text)
        metadata = {"backend": self.name, "mode": request.mode}
        return AgentResult(True, reply, request.session_id, metadata)
