from abc import ABC, abstractmethod

from tusk.schemas.chat_message import ChatMessage

__all__ = ["ConversationSummarizer"]


class ConversationSummarizer(ABC):
    @abstractmethod
    def summarize(self, messages: list[ChatMessage]) -> str:
        ...
