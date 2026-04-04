try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

from tusk.providers.llm.tool_response import message_content, needs_tool_fallback, tool_or_done
from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.llm.tool_use_failed_recovery import ToolUseFailedRecovery
from tusk.shared.schemas.tool_call import ToolCall

__all__ = ["GroqLLM", "_tool_or_done"]

_STRICT_SCHEMA_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b"})
_tool_or_done = tool_or_done


class GroqLLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if Groq is None:
            raise RuntimeError("groq package is not installed")
        self._client = Groq(api_key=api_key, timeout=30.0)
        self._model = model
        self._recovery = ToolUseFailedRecovery()
        self._logger = None

    @property
    def label(self) -> str:
        return f"groq/{self._model}"

    def set_payload_logger(self, logger: object) -> None:
        self._logger = logger

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        return self.complete_messages(system_prompt, [{"role": "user", "content": user_message}])

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        return message_content(self._create(_chat_payload(self._model, system_prompt, messages, 1024)))

    def complete_tool_call(self, system_prompt: str, messages: list[dict], tools: list[dict[str, object]]) -> ToolCall:
        payload = _chat_payload(self._model, system_prompt, messages, 1024)
        try:
            return tool_or_done(self._create({**payload, "tools": tools, "tool_choice": "required"}))
        except Exception as exc:
            return self._fallback_tool_call(exc, payload, tools)

    def complete_structured(self, system_prompt: str, user_message: str, schema_name: str, schema: dict, max_tokens: int = 256) -> str:
        payload = {**_chat_payload(self._model, system_prompt, [{"role": "user", "content": user_message}], max_tokens), "response_format": _response_format(self._model, schema_name, schema)}
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
            self._logger.before_request(self.label, payload)
        return self._client.chat.completions.create(**payload)


def _chat_payload(model: str, system_prompt: str, messages: list[dict], max_tokens: int) -> dict[str, object]:
    return {"model": model, "max_tokens": max_tokens, "messages": [{"role": "system", "content": system_prompt}, *messages]}


def _response_format(model: str, schema_name: str, schema: dict) -> dict:
    if model in _STRICT_SCHEMA_MODELS:
        return {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
    return {"type": "json_object"}
