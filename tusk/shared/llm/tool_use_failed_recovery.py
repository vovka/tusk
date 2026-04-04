import ast
import json
import re

from tusk.shared.schemas.tool_call import ToolCall, normalize_tool_name

__all__ = ["ToolUseFailedRecovery"]

_NAME = re.compile(r'"name"\s*:\s*"([^"]+)"')
_STATUS = re.compile(r'"status"\s*:\s*"([^"]+)"')
_SUMMARY = re.compile(r'"summary"\s*:\s*"((?:\\.|[^"\\])*)"')
_TEXT = re.compile(r'"text"\s*:\s*"((?:\\.|[^"\\])*)"')


class ToolUseFailedRecovery:
    def recover(self, exc: Exception) -> ToolCall | None:
        payload = self._payload(str(exc))
        return self._tool_call(payload)

    def _payload(self, text: str) -> dict | None:
        if "tool_use_failed" not in text or " - " not in text:
            return None
        try:
            return ast.literal_eval(text.split(" - ", 1)[1])
        except (SyntaxError, ValueError):
            generation = self._embedded_generation(text)
            return {"error": {"failed_generation": generation}} if generation else None

    def _tool_call(self, payload: dict | None) -> ToolCall | None:
        generation = self._failed_generation(payload)
        try:
            return self._built(json.loads(generation)) if generation else None
        except json.JSONDecodeError:
            return self._best_effort_done(generation)

    def _failed_generation(self, payload: dict | None) -> str:
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        return error.get("failed_generation", "") if isinstance(error, dict) else ""

    def _built(self, data: dict[str, object]) -> ToolCall | None:
        name = normalize_tool_name(data.get("name", ""))
        arguments = data.get("arguments", {})
        if not name or not isinstance(arguments, dict):
            return None
        return ToolCall(name, arguments, "")

    def _best_effort_done(self, generation: str) -> ToolCall | None:
        name = normalize_tool_name(self._match(_NAME, generation))
        status = self._match(_STATUS, generation)
        summary = self._decoded(_SUMMARY, generation)
        text = self._decoded(_TEXT, generation)
        if name != "done" or not status or not summary:
            return None
        arguments = {"status": status, "summary": summary}
        if text:
            arguments["text"] = text
        return ToolCall(name, arguments, "")

    def _match(self, pattern: re.Pattern[str], text: str) -> str:
        found = pattern.search(text)
        return found.group(1) if found else ""

    def _decoded(self, pattern: re.Pattern[str], text: str) -> str:
        value = self._match(pattern, text)
        if not value:
            return ""
        try:
            return json.loads(f'"{value}"')
        except json.JSONDecodeError:
            return ""

    def _embedded_generation(self, text: str) -> str:
        for marker in ("'failed_generation': '", '"failed_generation": "'):
            if marker in text:
                return text.split(marker, 1)[1]
        return ""
