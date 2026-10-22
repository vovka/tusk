import json

from tusk.shared.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.tools.tool_call import ToolCall

__all__ = ["LLMPayloadLogger"]


class LLMPayloadLogger:
    def __init__(self, log_printer: LogPrinter | None, slot_name: str, enabled_groups: frozenset[str] = frozenset(), preview_chars: int = 120) -> None:
        self._log = log_printer
        self._slot = slot_name
        self._enabled = enabled_groups
        self._preview = preview_chars

    def before_request(self, provider: str, payload: dict[str, object]) -> None:
        if self._log is None:
            return
        self._emit("LLMPAYLOAD", "payload", "llm-payload", {key: _schema_summary(value) for key, value in payload.items() if key != "tools"})
        if isinstance(payload.get("tools"), list):
            self._emit("LLMTOOLS", "tools", "llm-tools", payload["tools"])
        self._log.show_wait(provider, "llm-wait")

    def log_response(self, response: str | ToolCall) -> None:
        if self._log is None:
            return
        value = {"tool_name": response.tool_name, "call_id": response.call_id, "parameters": response.parameters} if isinstance(response, ToolCall) else {"content": str(response)}
        self._emit("LLMRESPONSE", "response", "llm-response", value)

    def _emit(self, tag: str, title: str, group: str, value: object) -> None:
        if f"{group}-full" in self._enabled:
            self._log.log(tag, f"[{self._slot}] {title}\n{json.dumps(value, ensure_ascii=False, indent=2)}", f"{group}-full")
        elif group in self._enabled:
            self._log.log(tag, f"[{self._slot}] {title}\n{json.dumps(_trimmed(value, self._preview), ensure_ascii=False)}", group)


def _schema_summary(value: object) -> object:
    if isinstance(value, dict) and "json_schema" in value:
        return {"type": value.get("type"), "name": value.get("json_schema", {}).get("name", "")}
    return value


def _trimmed(value: object, limit: int) -> object:
    if isinstance(value, dict):
        return {key: _trimmed(item, limit) for key, item in value.items()}
    if isinstance(value, list):
        return [_trimmed(item, limit) for item in value]
    return _middle(value, limit) if isinstance(value, str) else value


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
