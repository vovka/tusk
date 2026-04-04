from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.llm.llm_payload_logger import LLMPayloadLogger
from tusk.shared.llm.llm_retry_runner import LLMRetryRunner
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.tool_call import ToolCall

__all__ = ["LLMProxy"]


class LLMProxy(LLMProvider):
    def __init__(self, initial_provider: LLMProvider, log_printer: LogPrinter | None = None, slot_name: str = "", retry_runner: LLMRetryRunner | None = None, enabled_log_groups: frozenset[str] = frozenset(), preview_chars: int = 120) -> None:
        self._inner = initial_provider
        self._log = log_printer
        self._slot = slot_name or initial_provider.label
        self._retry = retry_runner or LLMRetryRunner()
        self._payload_logger = LLMPayloadLogger(log_printer, self._slot, enabled_log_groups, preview_chars)
        self._provider_logs_wait = self._bind(initial_provider)

    @property
    def label(self) -> str:
        return self._inner.label

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        self._log_request("complete")
        return self._logged(lambda: self._inner.complete(system_prompt, user_message, max_tokens))

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        self._log_request("messages")
        return self._logged(lambda: self._inner.complete_messages(system_prompt, messages))

    def complete_tool_call(self, system_prompt: str, messages: list[dict], tools: list[dict[str, object]]) -> ToolCall:
        self._log_request("tool-call")
        return self._logged(lambda: self._inner.complete_tool_call(system_prompt, messages, tools))

    def complete_structured(self, system_prompt: str, user_message: str, schema_name: str, schema: dict, max_tokens: int = 256) -> str:
        self._log_request("structured")
        return self._logged(lambda: self._inner.complete_structured(system_prompt, user_message, schema_name, schema, max_tokens))

    def swap(self, provider: LLMProvider) -> None:
        self._inner = provider
        self._provider_logs_wait = self._bind(provider)

    def _logged(self, operation: object) -> object:
        self._show_wait()
        try:
            result = self._retry.run(operation, self._log_retry)
        finally:
            if self._log:
                self._log.clear_wait()
        self._payload_logger.log_response(result)
        return result

    def _bind(self, provider: object) -> bool:
        setter = getattr(provider, "set_payload_logger", None)
        if not callable(setter):
            return False
        setter(self._payload_logger)
        return True

    def _show_wait(self) -> None:
        if self._log and not self._provider_logs_wait:
            self._log.show_wait(self.label, "llm-wait")

    def _log_request(self, kind: str) -> None:
        if self._log:
            self._log.log("LLMREQUEST", f"[{self._slot}] provider={self.label} kind={kind}", "llm-request")

    def _log_retry(self, exc: Exception, attempt: int) -> None:
        if self._log:
            self._log.log("LLMREQUEST", f"[{self._slot}] retry {attempt} after failure: {exc}", "llm-request")
