from collections.abc import Callable
from typing import TYPE_CHECKING

from tusk.providers.llm.tool_response import message_content, needs_tool_fallback, tool_or_done
from tusk.providers.llm.tool_use_failed_recovery import ToolUseFailedRecovery
from tusk.shared.interfaces.llm_provider import LLMProvider
from tusk.shared.llm.llm_payload_logger import LLMPayloadLogger
from tusk.shared.schemas.tools.tool_call import ToolCall

if TYPE_CHECKING:
    from groq import Groq
    from openai import OpenAI

__all__ = ["ChatCompletionsLLM"]

ResponseFormat = Callable[[str, dict], dict]


class ChatCompletionsLLM(LLMProvider):
    def __init__(self, client: "Groq | OpenAI", model: str, label: str, response_format: ResponseFormat | None = None) -> None:
        self._client = client
        self._model = model
        self._label = label
        self._response_format = response_format
        self._recovery = ToolUseFailedRecovery()
        self._logger: LLMPayloadLogger | None = None

    @property
    def label(self) -> str:
        return self._label

    def set_payload_logger(self, logger: LLMPayloadLogger) -> None:
        self._logger = logger

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        payload = self._chat_payload(system_prompt, [{"role": "user", "content": user_message}], max_tokens)
        return message_content(self._create(payload))

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        return message_content(self._create(self._chat_payload(system_prompt, messages, 1024)))

    def complete_tool_call(self, system_prompt: str, messages: list[dict], tools: list[dict[str, object]]) -> ToolCall:
        payload = self._chat_payload(system_prompt, messages, 1024)
        try:
            return tool_or_done(self._create({**payload, "tools": tools, "tool_choice": "required"}))
        except Exception as exc:
            return self._fallback_tool_call(exc, payload, tools)

    def complete_structured(self, system_prompt: str, user_message: str, schema_name: str, schema: dict, max_tokens: int = 256) -> str:
        payload = self._chat_payload(system_prompt, [{"role": "user", "content": user_message}], max_tokens)
        if self._response_format is not None:
            payload["response_format"] = self._response_format(schema_name, schema)
        return message_content(self._create(payload))

    def _fallback_tool_call(self, exc: Exception, payload: dict[str, object], tools: list[dict[str, object]]) -> ToolCall:
        recovered = self._recovery.recover(exc)
        if recovered is not None:
            return recovered
        if not needs_tool_fallback(exc):
            raise exc
        return tool_or_done(self._create({**payload, "tools": tools, "tool_choice": "auto"}))

    def _create(self, payload: dict[str, object]) -> object:
        if self._logger:
            self._logger.before_request(self._label, payload)
        return self._client.chat.completions.create(**payload)

    def _chat_payload(self, system_prompt: str, messages: list[dict], max_tokens: int) -> dict[str, object]:
        return {"model": self._model, "max_tokens": max_tokens, "messages": [{"role": "system", "content": system_prompt}, *messages]}
