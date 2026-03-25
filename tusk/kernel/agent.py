from tusk.kernel.agent_tool_loop import AgentToolLoop
from tusk.kernel.interfaces.agent import Agent
from tusk.kernel.interfaces.conversation_logger import ConversationLogger
from tusk.kernel.interfaces.conversation_history import ConversationHistory
from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.model_failure_reply_builder import ModelFailureReplyBuilder
from tusk.kernel.schemas.chat_message import ChatMessage
from tusk.kernel.terminal_tool_definition_list import TerminalToolDefinitionList
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["MainAgent"]

_SYSTEM_PROMPT = "\n".join([
    "You are TUSK, a desktop assistant.",
    "Use exactly one tool per response.",
    "Call one native tool on every turn.",
    "Think briefly before acting and follow a tool plan.",
    "Use done when no further action is needed.",
    "Use clarify when the request is ambiguous and you need one short question.",
    "Use unknown only when the request cannot be handled.",
    "All available tool names are listed below.",
    "Do not guess a tool schema or required arguments.",
    "If you want to use a tool and it has not already been described in this conversation, call describe_tool first.",
    "After a tool has been described once in this conversation, you may call it directly by name.",
    "You may also use run_tool with a tool name and input_json when that is simpler.",
    "Use find_tools if the right tool name is unclear.",
    "run_tool requires the target tool name and an input_json string containing a JSON object for that tool.",
    "Never use type_text for Enter, Delete, shortcuts, modifiers, or navigation keys.",
    "Use text tools only for literal printable text insertion.",
    "If paragraph breaks or shortcuts are needed, prefer press_keys over literal newline text.",
    "Do not repeat the same tool call with the same arguments more than twice in a row.",
    "If progress is unclear, inspect state with a tool or use clarify instead of looping.",
    "Example workflow:",
    "1. Read the command and identify the tool name you need.",
    "2. If that tool has not been described yet, call describe_tool with its name.",
    "3. Use the described schema to call the tool directly or through run_tool.",
    "4. Continue one tool at a time until the task is complete, then call done.",
])


class MainAgent(Agent):
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        history: ConversationHistory,
        log_printer: LogPrinter,
        usage_recorder: object,
        conversation_logger: ConversationLogger | None = None,
    ) -> None:
        self._registry = tool_registry
        self._history = history
        self._logger = conversation_logger
        self._terminal_tools = TerminalToolDefinitionList()
        self._loop = self._build_loop(llm_provider, tool_registry, log_printer, usage_recorder, conversation_logger)

    def process_command(self, command: str) -> str:
        reply = self._loop.run(self._prompt(), self._build_command_history(command), self._tools())
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

    def _tools(self) -> list[dict[str, object]]:
        return self._terminal_tools.build()

    def _prompt(self) -> str:
        return _SYSTEM_PROMPT + "\n" + self._registry.build_prompt_text()

    def _log_message(self, message: ChatMessage) -> None:
        if self._logger:
            self._logger.log_message(message)

    def _build_loop(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
        log_printer: LogPrinter,
        usage_recorder: object,
        conversation_logger: ConversationLogger | None,
    ) -> AgentToolLoop:
        return AgentToolLoop(
            llm_provider,
            tool_registry,
            log_printer,
            usage_recorder,
            conversation_logger,
            ModelFailureReplyBuilder(),
        )
