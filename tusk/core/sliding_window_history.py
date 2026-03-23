from tusk.interfaces.conversation_history import ConversationHistory
from tusk.interfaces.conversation_summarizer import ConversationSummarizer
from tusk.schemas.chat_message import ChatMessage

__all__ = ["SlidingWindowHistory"]

_SUMMARY_PREFIX = "Previous context summary: "


class SlidingWindowHistory(ConversationHistory):
    def __init__(
        self,
        max_messages: int,
        summarizer: ConversationSummarizer,
    ) -> None:
        self._max = max_messages
        self._summarizer = summarizer
        self._messages: list[ChatMessage] = []

    def get_messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def append(self, message: ChatMessage) -> None:
        self._messages.append(message)
        if len(self._messages) > self._max:
            self._compact()

    def clear(self) -> None:
        self._messages.clear()

    def _compact(self) -> None:
        evict_count = len(self._messages) // 2
        evicted = self._messages[:evict_count]
        self._messages = self._messages[evict_count:]
        summary_text = self._summarizer.summarize(evicted)
        summary = _build_summary_message(summary_text)
        self._messages.insert(0, summary)


def _build_summary_message(text: str) -> ChatMessage:
    return ChatMessage(role="user", content=_SUMMARY_PREFIX + text)
