from tusk.kernel.interfaces.agent import Agent
from tusk.kernel.interfaces.conversation_history import ConversationHistory
from tusk.lib.llm.interfaces.llm_provider import LLMProvider
from tusk.lib.logging.interfaces.log_printer import LogPrinter
from tusk.kernel.model_failure_reply_builder import ModelFailureReplyBuilder
from tusk.kernel.schemas.chat_message import ChatMessage
from tusk.kernel.terminal_tool_definition_list import TerminalToolDefinitionList
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["MainAgent"]

_PROMPT = "\n".join([
    "You are TUSK, a desktop assistant.",
    "Use execute_task for requests that require actions, tools, apps, desktop control, typing, clipboard, or model changes.",
    "Use done for conversational replies that need no task execution.",
    "Use clarify when one short question is required before acting.",
    "Use unknown when the request cannot be handled.",
    "execute_task returns the final task result to the user.",
    "Call exactly one tool.",
])


class MainAgent(Agent):
    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry, history: ConversationHistory, log_printer: LogPrinter) -> None:
        self._llm = llm_provider
        self._registry = tool_registry
        self._history = history
        self._log = log_printer
        self._terminal = TerminalToolDefinitionList()
        self._failure = ModelFailureReplyBuilder()

    def process_command(self, command: str) -> str:
        reply = self._reply(command)
        self._remember(command, reply)
        return reply

    def _reply(self, command: str) -> str:
        try:
            tool_call = self._llm.complete_tool_call(_PROMPT, self._history_for(command), self._tools())
        except Exception as exc:
            self._log.log("AGENT", f"llm failure: {exc}")
            return self._failure.build(exc)
        return self._tool_reply(tool_call, command)

    def _history_for(self, command: str) -> list[dict[str, str]]:
        prior = [item.to_dict() for item in self._history.get_messages()]
        return [*prior, ChatMessage("user", f"Command: {command}").to_dict()]

    def _tools(self) -> list[dict[str, object]]:
        return [*self._terminal.build(), *self._registry.definitions_for({"execute_task"})]

    def _tool_reply(self, tool_call: object, command: str) -> str:
        if tool_call.tool_name in {"done", "clarify", "unknown"}:
            return str(tool_call.parameters.get("reply", ""))
        if tool_call.tool_name != "execute_task":
            return "Use execute_task for actionable requests."
        result = self._registry.get("execute_task").execute({"task": tool_call.parameters.get("task", command)})
        return result.message

    def _remember(self, command: str, reply: str) -> None:
        self._history.append(ChatMessage("user", f"Command: {command}"))
        if reply:
            self._history.append(ChatMessage("assistant", reply))
