import json

from tusk.shared.schemas.tool_call import ToolCall

__all__ = ["inline_json", "message_line", "pretty_json", "response_line", "tool_line"]


def pretty_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def inline_json(value: object, limit: int) -> str:
    return _middle(json.dumps(value, ensure_ascii=False, sort_keys=True), limit)


def message_line(message: dict[str, object], limit: int) -> str:
    return '{ "role": ' + _quoted(str(message.get("role", ""))) + ', "content": ' + _quoted(_middle(str(message.get("content", "")), limit)) + " }"


def tool_line(tool: dict[str, object], limit: int) -> str:
    function = tool.get("function", {}) if isinstance(tool.get("function", {}), dict) else {}
    return '{ "type": "function", "function": { "name": ' + _quoted(str(function.get("name", ""))) + ', "description": ' + _quoted(_middle(str(function.get("description", "")), limit)) + " } }"


def response_line(value: str | ToolCall, limit: int) -> str:
    return _tool_response(value, limit) if isinstance(value, ToolCall) else '{ "content": ' + _quoted(_middle(str(value), limit)) + " }"


def _tool_response(value: ToolCall, limit: int) -> str:
    return '{ "tool_name": ' + _quoted(value.tool_name) + ', "call_id": ' + _quoted(value.call_id) + ', "arguments": ' + inline_json(value.parameters, limit) + " }"


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _middle(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = max(8, limit // 2)
    tail = max(8, limit - head)
    return _trim(text, head, tail)


def _trim(text: str, head: int, tail: int) -> str:
    omitted = len(text) - head - tail
    marker = f"...({omitted} chars more)..."
    shortened = text[:head] + marker + text[-tail:]
    return shortened if len(text) - len(shortened) >= 8 else text
