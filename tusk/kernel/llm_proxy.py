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
        slot_name: str = "",
    ) -> None:
        self._inner = initial_provider
        self._log = log_printer
        self._slot = slot_name or initial_provider.label

    @property
    def label(self) -> str:
        return self._inner.label

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        if self._log:
            self._log.show_wait(self.label, "wait")
            self._log_payload(system_prompt, [{"role": "user", "content": user_message}])
        try:
            return self._inner.complete(system_prompt, user_message, max_tokens)
        finally:
            if self._log:
                self._log.clear_wait()

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        if self._log:
            self._log.show_wait(self.label, "wait")
            self._log_payload(system_prompt, messages)
        try:
            return self._inner.complete_messages(system_prompt, messages)
        finally:
            if self._log:
                self._log.clear_wait()

    def complete_structured(
        self,
        system_prompt: str,
        user_message: str,
        schema_name: str,
        schema: dict,
        max_tokens: int = 256,
    ) -> str:
        if self._log:
            self._log.show_wait(self.label, "wait")
            self._log_payload(system_prompt, self._structured_messages(user_message), self._response_format(schema_name))
        try:
            return self._inner.complete_structured(system_prompt, user_message, schema_name, schema, max_tokens)
        finally:
            if self._log:
                self._log.clear_wait()

    def swap(self, provider: LLMProvider) -> None:
        self._inner = provider

    def _log_payload(self, system_prompt: str, messages: list[dict], response_format: dict | None = None) -> None:
        payload = {
            "slot": self._slot,
            "provider": self.label,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
        }
        if response_format:
            payload["response_format"] = response_format
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        self._log.log("LLM", f"[{self._slot}] payload\n{text}", "llm-with-payload")

    def _structured_messages(self, user_message: str) -> list[dict[str, str]]:
        return [{"role": "user", "content": user_message}]

    def _response_format(self, schema_name: str) -> dict[str, str]:
        return {"type": "json_schema", "name": schema_name}
