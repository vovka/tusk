try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_use_failed_recovery import ToolUseFailedRecovery

__all__ = ["OpenRouterLLM"]

_BASE_URL = "https://openrouter.ai/api/v1"
_APP_HEADERS = {
    "HTTP-Referer": "https://github.com/vovka/tusk",
    "X-Title": "TUSK",
}


class OpenRouterLLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package is not installed")
        self._client = OpenAI(api_key=api_key, base_url=_BASE_URL, default_headers=_APP_HEADERS, timeout=15.0)
        self._model = model
        self._recovery = ToolUseFailedRecovery()

    @property
    def label(self) -> str:
        return f"openrouter/{self._model}"

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        return self.complete_messages(system_prompt, [{"role": "user", "content": user_message}])

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(**_chat_payload(self._model, system_prompt, messages))
        content = response.choices[0].message.content
        if isinstance(content, str) and content.strip():
            return content
        raise RuntimeError("empty completion from openrouter provider")

    def complete_tool_call(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict[str, object]],
    ) -> ToolCall:
        payload = _chat_payload(self._model, system_prompt, messages)
        try:
            response = self._create_tool_response(payload, tools, "required")
        except Exception as exc:
            recovered = self._recovery.recover(exc)
            if recovered is not None:
                return recovered
            response = self._fallback_response(exc, payload, tools)
        return _tool_or_done(response)

    def complete_structured(
        self,
        system_prompt: str,
        user_message: str,
        schema_name: str,
        schema: dict,
        max_tokens: int = 256,
    ) -> str:
        return self.complete(system_prompt, user_message, max_tokens)

    def _create_tool_response(self, payload: dict[str, object], tools: list[dict[str, object]], choice: str) -> object:
        return self._client.chat.completions.create(**{**payload, "tools": tools, "tool_choice": choice})

    def _fallback_response(self, exc: Exception, payload: dict[str, object], tools: list[dict[str, object]]) -> object:
        if not _needs_tool_fallback(exc):
            raise exc
        return self._create_tool_response(payload, tools, "auto")


def _chat_payload(model: str, system_prompt: str, messages: list[dict]) -> dict[str, object]:
    return {"model": model, "max_tokens": 1024, "messages": [{"role": "system", "content": system_prompt}, *messages]}


def _first_tool_call(response: object) -> ToolCall:
    import json

    tool_calls = response.choices[0].message.tool_calls or []
    if not tool_calls:
        raise RuntimeError("missing tool call from openrouter provider")
    call = tool_calls[0]
    arguments = json.loads(call.function.arguments or "{}")
    return ToolCall(call.function.name, arguments, call.id or "")


def _tool_or_done(response: object) -> ToolCall:
    tool_calls = response.choices[0].message.tool_calls or []
    return _first_tool_call(response) if tool_calls else ToolCall("done", {"reply": _message_text(response)}, "")


def _message_text(response: object) -> str:
    content = response.choices[0].message.content
    if isinstance(content, str) and content.strip():
        return content
    raise RuntimeError("empty completion from openrouter provider")


def _needs_tool_fallback(exc: Exception) -> bool:
    text = str(exc)
    return "Tool choice is required" in text and "did not call a tool" in text
