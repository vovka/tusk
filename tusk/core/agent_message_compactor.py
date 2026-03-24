import json

from tusk.interfaces.message_compactor import MessageCompactor
from tusk.schemas.chat_message import ChatMessage

__all__ = ["AgentMessageCompactor"]

_TOOL_RESULT_PREFIX = "Tool result: "
_MAX_TOOL_RESULT_LENGTH = 80
_MAX_TRUNCATED_ASSISTANT = 100
_HALF_TRUNCATE = 33


class AgentMessageCompactor(MessageCompactor):
    def compact(self, message: ChatMessage) -> ChatMessage:
        if message.role == "user" and message.content.startswith(_TOOL_RESULT_PREFIX):
            return ChatMessage(message.role, _compact_tool_result(message.content))
        if message.role == "assistant":
            return ChatMessage(message.role, _compact_assistant(message.content))
        return message


def _compact_assistant(content: str) -> str:
    try:
        data = json.loads(content.strip())
        tool = data.get("tool", "unknown")
        reply = data.get("reply", "")
        return f"[{tool}] {reply}"
    except (json.JSONDecodeError, AttributeError):
        return content[:_MAX_TRUNCATED_ASSISTANT]


def _compact_tool_result(content: str) -> str:
    if len(content) <= _MAX_TOOL_RESULT_LENGTH:
        return content
    prefix = content[:_HALF_TRUNCATE]
    suffix = content[-_HALF_TRUNCATE:]
    return f"{prefix}...{suffix}"
