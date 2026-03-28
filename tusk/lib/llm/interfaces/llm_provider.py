from abc import ABC, abstractmethod
from tusk.kernel.schemas.tool_call import ToolCall

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

    @abstractmethod
    def complete_tool_call(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict[str, object]],
    ) -> ToolCall:
        ...

    @abstractmethod
    def complete_structured(
        self,
        system_prompt: str,
        user_message: str,
        schema_name: str,
        schema: dict,
        max_tokens: int = 256,
    ) -> str:
        ...
