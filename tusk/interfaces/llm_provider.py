from abc import ABC, abstractmethod

__all__ = ["LLMProvider"]


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_message: str) -> str:
        ...
