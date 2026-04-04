try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from tusk.providers.llm.tool_response import message_content, needs_tool_fallback, tool_or_done
from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.llm.tool_use_failed_recovery import ToolUseFailedRecovery
from tusk.shared.schemas.tool_call import ToolCall

__all__ = ["OpenRouterLLM", "_tool_or_done"]

_BASE_URL = "https://openrouter.ai/api/v1"
_APP_HEADERS = {"HTTP-Referer": "https://github.com/vovka/tusk", "X-Title": "TUSK"}
_tool_or_done = tool_or_done


class OpenRouterLLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package is not installed")
        self._client = OpenAI(api_key=api_key, base_url=_BASE_URL, default_headers=_APP_HEADERS, timeout=15.0)
        self._model = model
        self._recovery = ToolUseFailedRecovery()
        self._logger = None

    @property
    def label(self) -> str:
        return f"openrouter/{self._model}"

    def set_payload_logger(self, logger: object) -> None:
        self._logger = logger

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        return self.complete_messages(system_prompt, [{"role": "user", "content": user_message}])

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        return message_content(self._create(_chat_payload(self._model, system_prompt, messages)))

    def complete_tool_call(self, system_prompt: str, messages: list[dict], tools: list[dict[str, object]]) -> ToolCall:
        payload = _chat_payload(self._model, system_prompt, messages)
        try:
            return tool_or_done(self._create({**payload, "tools": tools, "tool_choice": "required"}))
        except Exception as exc:
            return self._fallback_tool_call(exc, payload, tools)

    def complete_structured(self, system_prompt: str, user_message: str, schema_name: str, schema: dict, max_tokens: int = 256) -> str:
        return self.complete(system_prompt, user_message, max_tokens)

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


def _chat_payload(model: str, system_prompt: str, messages: list[dict]) -> dict[str, object]:
    return {"model": model, "max_tokens": 1024, "messages": [{"role": "system", "content": system_prompt}, *messages]}
