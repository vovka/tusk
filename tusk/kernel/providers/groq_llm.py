try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.schemas.tool_call import ToolCall
from tusk.kernel.tool_use_failed_recovery import ToolUseFailedRecovery

__all__ = ["GroqLLM"]

_STRICT_SCHEMA_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b"})


class GroqLLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if Groq is None:
            raise RuntimeError("groq package is not installed")
        self._client = Groq(api_key=api_key, timeout=30.0)
        self._model = model
        self._recovery = ToolUseFailedRecovery()

    @property
    def label(self) -> str:
        return f"groq/{self._model}"

    def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str:
        return self.complete_messages(system_prompt, [{"role": "user", "content": user_message}])

    def complete_messages(self, system_prompt: str, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(**_chat_payload(self._model, system_prompt, messages, 1024))
        return _message_content(response)

    def complete_tool_call(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict[str, object]],
    ) -> ToolCall:
        payload = _chat_payload(self._model, system_prompt, messages, 1024)
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
        response = self._client.chat.completions.create(**self._structured_payload(
            system_prompt,
            user_message,
            schema_name,
            schema,
            max_tokens,
        ))
        return _message_content(response)

    def _structured_payload(
        self,
        system_prompt: str,
        user_message: str,
        schema_name: str,
        schema: dict,
        max_tokens: int,
    ) -> dict:
        return {
            **_chat_payload(self._model, system_prompt, [{"role": "user", "content": user_message}], max_tokens),
            "response_format": _response_format(self._model, schema_name, schema),
        }

    def _create_tool_response(self, payload: dict[str, object], tools: list[dict[str, object]], choice: str) -> object:
        return self._client.chat.completions.create(**{**payload, "tools": tools, "tool_choice": choice})

    def _fallback_response(self, exc: Exception, payload: dict[str, object], tools: list[dict[str, object]]) -> object:
        if not _needs_tool_fallback(exc): raise exc
        return self._create_tool_response(payload, tools, "auto")


def _chat_payload(model: str, system_prompt: str, messages: list[dict], max_tokens: int) -> dict[str, object]:
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
    }


def _response_format(model: str, schema_name: str, schema: dict) -> dict:
    if model in _STRICT_SCHEMA_MODELS:
        return {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
    return {"type": "json_object"}


def _message_content(response: object) -> str:
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("empty completion from groq provider")
    return content


def _first_tool_call(response: object) -> ToolCall:
    tool_calls = response.choices[0].message.tool_calls or []
    if not tool_calls:
        raise RuntimeError("missing tool call from groq provider")
    call = tool_calls[0]
    return ToolCall(call.function.name, _arguments(call), call.id or "")


def _tool_or_done(response: object) -> ToolCall:
    tool_calls = response.choices[0].message.tool_calls or []
    return _first_tool_call(response) if tool_calls else ToolCall("done", {"reply": _message_content(response)}, "")


def _needs_tool_fallback(exc: Exception) -> bool:
    return "Tool choice is required" in str(exc) and "did not call a tool" in str(exc)


def _arguments(call: object) -> dict[str, object]:
    return __import__("json").loads(call.function.arguments or "{}")
