from tusk.kernel.agent import AgentOrchestrator, AgentRunRequest
from tusk.kernel.agent_backends import AgentBackend, AgentRequest
from tusk.kernel.agent_backends import AgentResult as BackendAgentResult
from tusk.kernel.interfaces.conversation_history import ConversationHistory
from tusk.shared.schemas.chat_message import ChatMessage

__all__ = ["MainAgent"]


class MainAgent(AgentBackend):
    def __init__(self, orchestrator: AgentOrchestrator, history: ConversationHistory) -> None:
        self._orchestrator = orchestrator
        self._history = history
        self._session_id = ""

    def run(self, request: AgentRequest) -> BackendAgentResult:
        self._session_id = request.session_id
        reply = self.process_command(request.user_text)
        return BackendAgentResult(True, reply, self._session_id)

    def process_command(self, command: str) -> str:
        result = self._orchestrator.run(AgentRunRequest(command, "conversation", self._session_id))
        self._session_id = result.session_id
        reply = result.reply_text()
        self._remember(command, reply)
        return reply

    def _remember(self, command: str, reply: str) -> None:
        self._history.append(ChatMessage("user", f"Command: {command}"))
        if reply:
            self._history.append(ChatMessage("assistant", reply))
