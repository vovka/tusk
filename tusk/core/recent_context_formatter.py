from tusk.interfaces.conversation_history import ConversationHistory
from tusk.schemas.chat_message import ChatMessage

__all__ = ["RecentContextFormatter"]

_DEFAULT_MAX_MESSAGES = 6
_MAX_CONTENT_LENGTH = 150


class RecentContextFormatter:
    def __init__(
        self,
        history: ConversationHistory,
        max_messages: int = _DEFAULT_MAX_MESSAGES,
    ) -> None:
        self._history = history
        self._max = max_messages

    def format_recent_context(self) -> str:
        messages = self._history.get_messages()
        recent = messages[-self._max:]
        if not recent:
            return ""
        return self._render(recent)

    def _render(self, messages: list[ChatMessage]) -> str:
        lines = [self._format_message(m) for m in messages]
        return "\n".join(lines)

    def _format_message(self, message: ChatMessage) -> str:
        label = "User" if message.role == "user" else "TUSK"
        truncated = message.content[:_MAX_CONTENT_LENGTH]
        return f"  {label}: {truncated}"
