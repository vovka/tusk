import json

from tusk.shared.schemas.tool_call import ToolCall

__all__ = ["message_content", "needs_tool_fallback", "tool_or_done"]


def message_content(response: object) -> str:
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("empty completion from provider")
    return content


def tool_or_done(response: object) -> ToolCall:
    calls = response.choices[0].message.tool_calls or []
    return _first_tool_call(calls[0]) if calls else ToolCall("done", {"reply": message_content(response)}, "")


def needs_tool_fallback(exc: Exception) -> bool:
    text = str(exc)
    return "Tool choice is required" in text and "did not call a tool" in text


def _first_tool_call(call: object) -> ToolCall:
    return ToolCall(call.function.name, _arguments(call), call.id or "")


def _arguments(call: object) -> dict[str, object]:
    return json.loads(call.function.arguments or "{}")
