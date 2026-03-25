from abc import ABC, abstractmethod

from tusk.kernel.interfaces.llm_provider import LLMProvider

__all__ = ["LLMProviderFactory"]


class LLMProviderFactory(ABC):
    @abstractmethod
    def create(self, provider_name: str, model: str) -> LLMProvider:
        ...
