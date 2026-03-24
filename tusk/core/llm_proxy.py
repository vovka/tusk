from tusk.interfaces.llm_provider import LLMProvider
from tusk.interfaces.log_printer import LogPrinter

__all__ = ["LLMProxy"]


class LLMProxy(LLMProvider):
    def __init__(self, initial_provider: LLMProvider, log_printer: LogPrinter) -> None:
        self._inner = initial_provider
        self._log = log_printer

    @property
    def label(self) -> str:
        return self._inner.label

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        self._log.show_wait(self.label)
        try:
            return self._inner.complete(system_prompt, user_message, max_tokens)
        finally:
            self._log.clear_wait()

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        self._log.show_wait(self.label)
        try:
            return self._inner.complete_messages(system_prompt, messages)
        finally:
            self._log.clear_wait()

    def swap(self, provider: LLMProvider) -> None:
        self._inner = provider
