from collections.abc import Callable
from typing import TypeVar

from tusk.shared.interfaces.llm_provider import LLMProvider
from tusk.shared.llm.llm_payload_logger import LLMPayloadLogger
from tusk.shared.schemas.tools.tool_call import ToolCall

__all__ = ["RotatingLLMProvider"]

T = TypeVar("T")


class RotatingLLMProvider(LLMProvider):
    """Spreads requests round-robin over models that each have their own rate limit; a 429 moves to the next one."""

    def __init__(self, providers: list[LLMProvider], on_failover: Callable[[Exception, str], None] | None = None) -> None:
        self._providers = providers
        self._next = 0
        self._on_failover = on_failover

    @property
    def label(self) -> str:
        return self._providers[self._next].label

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        return self._rotate(lambda p: p.complete(system_prompt, user_message, max_tokens))

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        return self._rotate(lambda p: p.complete_messages(system_prompt, messages))

    def complete_tool_call(self, system_prompt: str, messages: list[dict], tools: list[dict[str, object]]) -> ToolCall:
        return self._rotate(lambda p: p.complete_tool_call(system_prompt, messages, tools))

    def complete_structured(self, system_prompt: str, user_message: str, schema_name: str, schema: dict, max_tokens: int = 256) -> str:
        return self._rotate(lambda p: p.complete_structured(system_prompt, user_message, schema_name, schema, max_tokens))

    def set_payload_logger(self, logger: LLMPayloadLogger) -> None:
        for provider in self._providers:
            provider.set_payload_logger(logger)

    def _rotate(self, operation: Callable[[LLMProvider], T]) -> T:
        # all models rate-limited: the last 429 propagates so the proxy's retry runner sleeps once
        for _ in range(len(self._providers) - 1):
            try:
                return operation(self._take())
            except Exception as exc:
                if not _rate_limited(exc):
                    raise
                self._notify(exc)
        return operation(self._take())

    def _take(self) -> LLMProvider:
        provider = self._providers[self._next]
        self._next = (self._next + 1) % len(self._providers)
        return provider

    def _notify(self, exc: Exception) -> None:
        if self._on_failover:
            self._on_failover(exc, self.label)


def _rate_limited(exc: Exception) -> bool:
    code = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    return code == 429 or "429" in str(exc)
