from abc import ABC, abstractmethod

from tusk.schemas.chat_message import ChatMessage

__all__ = ["MessageCompactor"]


class MessageCompactor(ABC):
    @abstractmethod
    def compact(self, message: ChatMessage) -> ChatMessage:
        """Return a compacted version of the message for history storage."""
        ...
