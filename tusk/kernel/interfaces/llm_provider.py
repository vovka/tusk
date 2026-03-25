from abc import ABC, abstractmethod

__all__ = ["LLMProvider"]


class LLMProvider(ABC):
    @property
    @abstractmethod
    def label(self) -> str:
        ...

    @abstractmethod
    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        ...

    @abstractmethod
    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        ...
