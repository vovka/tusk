from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.llm.llm_payload_logger import LLMPayloadLogger
from tusk.shared.llm.llm_retry_runner import LLMRetryRunner
from tusk.shared.schemas.tool_call import ToolCall

__all__ = ["LLMProxy"]


class LLMProxy(LLMProvider):
    def __init__(
        self,
        initial_provider: LLMProvider,
        log_printer: LogPrinter | None = None,
        slot_name: str = "",
        retry_runner: LLMRetryRunner | None = None,
    ) -> None:
        self._inner = initial_provider
        self._log = log_printer
        self._slot = slot_name or initial_provider.label
        self._retry = retry_runner or LLMRetryRunner()
        self._payload_logger = LLMPayloadLogger(log_printer, self._slot, lambda: self.label)

    @property
    def label(self) -> str:
        return self._inner.label

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        if self._log:
            self._log.show_wait(self.label, "llm-wait")
            self._log_request("complete")
            self._payload_logger.log(system_prompt, [{"role": "user", "content": user_message}])
        try:
            return self._run(lambda: self._inner.complete(system_prompt, user_message, max_tokens))
        finally:
            if self._log:
                self._log.clear_wait()

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        if self._log:
            self._log.show_wait(self.label, "llm-wait")
            self._log_request("messages")
            self._payload_logger.log(system_prompt, messages)
        try:
            return self._run(lambda: self._inner.complete_messages(system_prompt, messages))
        finally:
            if self._log:
                self._log.clear_wait()

    def complete_tool_call(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict[str, object]],
    ) -> ToolCall:
        if self._log:
            self._log.show_wait(self.label, "llm-wait")
            self._log_request("tool-call")
            self._payload_logger.log(system_prompt, messages, tools=tools)
        try:
            return self._run(lambda: self._inner.complete_tool_call(system_prompt, messages, tools))
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
            self._log.show_wait(self.label, "llm-wait")
            self._log_request("structured")
            self._payload_logger.log(system_prompt, self._structured_messages(user_message), self._response_format(schema_name))
        try:
            return self._run(lambda: self._inner.complete_structured(system_prompt, user_message, schema_name, schema, max_tokens))
        finally:
            if self._log:
                self._log.clear_wait()

    def swap(self, provider: LLMProvider) -> None:
        self._inner = provider

    def _structured_messages(self, user_message: str) -> list[dict[str, str]]:
        return [{"role": "user", "content": user_message}]

    def _response_format(self, schema_name: str) -> dict[str, str]:
        return {"type": "json_schema", "name": schema_name}

    def _run(self, operation: object) -> object:
        return self._retry.run(operation, self._log_retry)

    def _log_request(self, kind: str) -> None:
        if self._log:
            self._log.log("LLMREQUEST", f"[{self._slot}] provider={self.label} kind={kind}", "llm-request")

    def _log_retry(self, exc: Exception, attempt: int) -> None:
        if self._log:
            self._log.log("LLMREQUEST", f"[{self._slot}] retry {attempt} after failure: {exc}", "llm-request")
