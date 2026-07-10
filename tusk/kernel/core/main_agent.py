from tusk.kernel.agent import AgentOrchestrator, AgentRunRequest
from tusk.kernel.agent.backends import AgentBackend, AgentRequest
from tusk.kernel.agent.backends import AgentResult as BackendAgentResult
from tusk.kernel.agent.session.store import Store
from tusk.kernel.interfaces.conversation_history import ConversationHistory
from tusk.shared.schemas.chat_message import ChatMessage

__all__ = ["MainAgent"]


class MainAgent(AgentBackend):
    def __init__(self, orchestrator: AgentOrchestrator, history: ConversationHistory, session_store: Store | None = None) -> None:
        self._orchestrator = orchestrator
        self._history = history
        self._store = session_store
        self._session_id = ""

    def run(self, request: AgentRequest) -> BackendAgentResult:
        self._session_id = request.session_id
        reply = self.process_command(request.user_text, request.mode)
        return BackendAgentResult(True, reply, self._session_id)

    def process_command(self, command: str, kind: str = "conversation") -> str:
        if kind == "command":
            return self._fast_command(command)
        return self._conversation(command)

    def _conversation(self, command: str) -> str:
        result = self._orchestrator.run(AgentRunRequest(command, "conversation", self._session_id))
        self._session_id = result.session_id
        return self._finished(command, result)

    def _fast_command(self, command: str) -> str:
        # fresh session with all runtime tools: tool schemas never enter the conversation context
        result = self._orchestrator.run(AgentRunRequest(command, "command", "", runtime_tool_names=("*",)))
        reply = self._finished(command, result)
        self._share_with_conversation(command, reply)
        return reply

    def _finished(self, command: str, result: object) -> str:
        reply = "Stopped." if result.status == "cancelled" else result.reply_text()
        self._remember(command, reply)
        return reply

    def _share_with_conversation(self, command: str, reply: str) -> None:
        # one plain line per side keeps the conversation agent aware of fast-path commands
        if self._store is None or not self._session_id:
            return
        self._append_line("user", command)
        self._append_line("assistant", f"[did: {reply}]" if reply else "[did: completed]")

    def _append_line(self, role: str, content: str) -> None:
        self._store.append_event(self._session_id, "message_appended", {"role": role, "content": content})

    def _remember(self, command: str, reply: str) -> None:
        self._history.append(ChatMessage("user", f"Command: {command}"))
        if reply:
            self._history.append(ChatMessage("assistant", reply))
