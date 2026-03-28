from abc import ABC, abstractmethod

from tusk.kernel.schemas.chat_message import ChatMessage

__all__ = ["ConversationHistory"]


class ConversationHistory(ABC):
    @abstractmethod
    def get_messages(self) -> list[ChatMessage]:
        ...

    @abstractmethod
    def append(self, message: ChatMessage) -> None:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...
