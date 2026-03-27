from abc import ABC, abstractmethod

from tusk.kernel.schemas.chat_message import ChatMessage

__all__ = ["ConversationLogger"]


class ConversationLogger(ABC):
    @abstractmethod
    def log_message(self, message: ChatMessage) -> None:
        ...
