from __future__ import annotations

import json

from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.log_printer import LogPrinter

__all__ = ["LLMProxy"]


class LLMProxy(LLMProvider):
    def __init__(
        self,
        initial_provider: LLMProvider,
        log_printer: LogPrinter | None = None,
    ) -> None:
        self._inner = initial_provider
        self._log = log_printer

    @property
    def label(self) -> str:
        return self._inner.label

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        if self._log:
            self._log.show_wait(self.label)
            self._log_payload(system_prompt, [{"role": "user", "content": user_message}])
        try:
            return self._inner.complete(system_prompt, user_message, max_tokens)
        finally:
            if self._log:
                self._log.clear_wait()

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        if self._log:
            self._log.show_wait(self.label)
            self._log_payload(system_prompt, messages)
        try:
            return self._inner.complete_messages(system_prompt, messages)
        finally:
            if self._log:
                self._log.clear_wait()

    def swap(self, provider: LLMProvider) -> None:
        self._inner = provider

    def _log_payload(self, system_prompt: str, messages: list[dict]) -> None:
        payload = {
            "label": self.label,
            "system_prompt": system_prompt,
            "messages": messages,
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        self._log.log("LLMPAYLOAD", text)
