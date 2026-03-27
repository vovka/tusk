import ast
import json

from tusk.kernel.schemas.tool_call import ToolCall

__all__ = ["ToolUseFailedRecovery"]


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
            return None

    def _tool_call(self, payload: dict | None) -> ToolCall | None:
        generation = self._failed_generation(payload)
        try:
            return self._built(json.loads(generation)) if generation else None
        except json.JSONDecodeError:
            return None

    def _failed_generation(self, payload: dict | None) -> str:
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        return error.get("failed_generation", "") if isinstance(error, dict) else ""

    def _built(self, data: dict[str, object]) -> ToolCall | None:
        name = str(data.get("name", "")).strip()
        arguments = data.get("arguments", {})
        if not name or not isinstance(arguments, dict):
            return None
        return ToolCall(name, arguments, "")
