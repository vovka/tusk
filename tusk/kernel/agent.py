from tusk.kernel.interfaces.agent import Agent
from tusk.kernel.interfaces.conversation_history import ConversationHistory
from tusk.kernel.schemas.chat_message import ChatMessage
from tusk.lib.agent import AgentOrchestrator, AgentRunRequest

__all__ = ["MainAgent"]


class MainAgent(Agent):
    def __init__(self, orchestrator: AgentOrchestrator, history: ConversationHistory) -> None:
        self._orchestrator = orchestrator
        self._history = history
        self._session_id = ""

    def process_command(self, command: str) -> str:
        result = self._orchestrator.run(AgentRunRequest(command, "conversation", self._session_id))
        self._session_id = result.session_id
        reply = result.reply_text()
        self._history.append(ChatMessage("user", f"Command: {command}"))
        if reply:
            self._history.append(ChatMessage("assistant", reply))
        return reply
