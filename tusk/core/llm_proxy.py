from tusk.interfaces.llm_provider import LLMProvider

__all__ = ["LLMProxy"]


class LLMProxy(LLMProvider):
    def __init__(self, initial_provider: LLMProvider) -> None:
        self._inner = initial_provider

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        return self._inner.complete(system_prompt, user_message, max_tokens)

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        return self._inner.complete_messages(system_prompt, messages)

    def swap(self, provider: LLMProvider) -> None:
        self._inner = provider
