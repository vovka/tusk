from tusk.kernel.agent_tool_loop import AgentToolLoop
from tusk.kernel.desktop_context_message_builder import DesktopContextMessageBuilder
from tusk.kernel.interfaces.agent import Agent
from tusk.kernel.interfaces.conversation_logger import ConversationLogger
from tusk.kernel.interfaces.conversation_history import ConversationHistory
from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.schemas.chat_message import ChatMessage
from tusk.kernel.tool_registry import ToolRegistry
from tusk.kernel.tool_call_parser import ToolCallParser
from tusk.kernel.model_failure_reply_builder import ModelFailureReplyBuilder

__all__ = ["MainAgent"]

_SYSTEM_PROMPT = "\n".join([
    "You are TUSK, a desktop assistant.",
    "Use exactly one tool per response.",
    'Respond with JSON only.',
    'Every response must include "tool" and "reply".',
    'Use {"tool":"done","reply":"<final response>"} when no tool is needed.',
    'Use {"tool":"clarify","reply":"<question>"} if the request is ambiguous and you need a short follow-up question.',
    'Use {"tool":"unknown","reply":"<brief response>","reason":"<why>"} only when the request cannot be handled.',
    'When calling a tool, return a flat JSON object like {"tool":"gnome.launch_application","reply":"Opening gedit.","application_name":"gedit"}.',
    "Available tools:",
])


class MainAgent(Agent):
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        history: ConversationHistory,
        context_provider: object,
        log_printer: LogPrinter,
        conversation_logger: ConversationLogger | None = None,
    ) -> None:
        self._registry = tool_registry
        self._history = history
        self._context = context_provider
        self._logger = conversation_logger
        self._loop = self._build_loop(llm_provider, tool_registry, log_printer, conversation_logger)
        self._context_builder = DesktopContextMessageBuilder()

    def process_command(self, command: str) -> str:
        context = self._context.get_context()
        prompt = self._build_system_prompt()
        reply = self._loop.run(
            prompt,
            self._context_builder.build(context),
            self._build_command_history(command),
        )
        self._remember_exchange(command, reply)
        return reply

    def _build_command_history(self, command: str) -> list[dict[str, str]]:
        prior = [item.to_dict() for item in self._history.get_messages()]
        return [*prior, ChatMessage("user", f"Command: {command}").to_dict()]

    def _remember_exchange(self, command: str, reply: str) -> None:
        user = ChatMessage("user", f"Command: {command}")
        self._log_message(user)
        self._history.append(user)
        if reply:
            assistant = ChatMessage("assistant", reply)
            self._log_message(assistant)
            self._history.append(assistant)

    def _build_system_prompt(self) -> str:
        return "\n".join([_SYSTEM_PROMPT, self._registry.build_schema_text()])

    def _log_message(self, message: ChatMessage) -> None:
        if self._logger:
            self._logger.log_message(message)

    def _build_loop(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        log_printer: LogPrinter,
        conversation_logger: ConversationLogger | None,
    ) -> AgentToolLoop:
        return AgentToolLoop(
            llm_provider,
            tool_registry,
            log_printer,
            conversation_logger,
            ToolCallParser(log_printer),
            ModelFailureReplyBuilder(),
        )
