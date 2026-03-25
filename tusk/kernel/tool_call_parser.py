import json

from tusk.kernel.interfaces.log_printer import LogPrinter
from tusk.kernel.schemas.tool_call import ToolCall

__all__ = ["ToolCallParser"]


class ToolCallParser:
    def __init__(self, log_printer: LogPrinter) -> None:
        self._log = log_printer

    def parse(self, raw: str) -> ToolCall:
        try:
            return self._load(raw)
        except Exception as exc:
            self._log.log("AGENT", f"invalid JSON from model: {exc}")
            return self._fallback()

    def _load(self, raw: str) -> ToolCall:
        data = json.loads(raw.strip())
        return ToolCall(tool_name=data.pop("tool"), parameters=data)

    def _fallback(self) -> ToolCall:
        return ToolCall("unknown", self._fallback_parameters())

    def _fallback_parameters(self) -> dict[str, str]:
        return {
            "reply": "I could not interpret the model response.",
            "reason": "model did not return valid tool JSON",
        }
