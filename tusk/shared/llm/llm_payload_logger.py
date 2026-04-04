from tusk.shared.llm.llm_log_text import inline_json, message_line, pretty_json, response_line, tool_line
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.tool_call import ToolCall

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
        self._log_payload(payload)
        self._log_tools(payload.get("tools"))
        self._log.show_wait(provider, "llm-wait")

    def log_response(self, response: str | ToolCall) -> None:
        group = self._mode("llm-response", "llm-response-full")
        if group:
            self._emit("LLMRESPONSE", "response", group, self._response_text(response, group.endswith("-full")))

    def _log_payload(self, payload: dict[str, object]) -> None:
        group = self._mode("llm-payload", "llm-payload-full")
        if group:
            self._emit("LLMPAYLOAD", "payload", group, self._payload_text(payload, group.endswith("-full")))

    def _log_tools(self, tools: object) -> None:
        group = self._mode("llm-tools", "llm-tools-full")
        if group and isinstance(tools, list):
            self._emit("LLMTOOLS", "tools", group, pretty_json(tools) if group.endswith("-full") else self._tool_text(tools))

    def _emit(self, tag: str, title: str, group: str, text: str) -> None:
        self._log.log(tag, f"[{self._slot}] {title}\n{text}", group)

    def _mode(self, compact: str, full: str) -> str:
        return full if full in self._enabled else compact if compact in self._enabled else ""

    def _payload_text(self, payload: dict[str, object], full: bool) -> str:
        body = {key: self._summary(payload[key]) for key in payload if key != "tools"}
        return pretty_json(body) if full else self._compact_payload(body)

    def _summary(self, value: object) -> object:
        return {"type": value.get("type"), "name": value.get("json_schema", {}).get("name", "")} if isinstance(value, dict) and "json_schema" in value else value

    def _compact_payload(self, payload: dict[str, object]) -> str:
        items = list(payload.items())
        return "\n".join(["{", *[line for index, item in enumerate(items) for line in self._field_lines(item[0], item[1], index == len(items) - 1)], "}"])

    def _field_lines(self, key: str, value: object, last: bool) -> list[str]:
        return self._message_lines(value, last) if key == "messages" else [f'  "{key}": {inline_json(value, self._preview) if isinstance(value, (dict, list)) else pretty_json(value)}' + self._comma(last)]

    def _message_lines(self, value: object, last: bool) -> list[str]:
        items = list(value) if isinstance(value, list) else []
        return ['  "messages": [', *[f"    {message_line(item, self._preview)}" + self._comma(index == len(items) - 1) for index, item in enumerate(items)], f"  ]{self._comma(last)}"]

    def _tool_text(self, tools: list[dict[str, object]]) -> str:
        return "\n".join(["[", *[f"  {tool_line(tool, self._preview)}" + self._comma(index == len(tools) - 1) for index, tool in enumerate(tools)], "]"])

    def _response_text(self, response: str | ToolCall, full: bool) -> str:
        return pretty_json(self._response_value(response)) if full else response_line(response, self._preview)

    def _response_value(self, response: str | ToolCall) -> object:
        return {"tool_name": response.tool_name, "call_id": response.call_id, "parameters": response.parameters} if isinstance(response, ToolCall) else {"content": str(response)}

    def _comma(self, last: bool) -> str:
        return "" if last else ","
