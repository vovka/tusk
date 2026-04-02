import json

from tusk.shared.schemas.tool_result import ToolResult

__all__ = ["ChildResultMessageBuilder"]


class ChildResultMessageBuilder:
    def build(self, tool_result: ToolResult) -> str | None:
        child = self._child_result(tool_result)
        if child is None:
            return None
        return "\n".join(["[child-result]", *self._lines(child)])

    def _child_result(self, tool_result: ToolResult) -> dict[str, object] | None:
        if not tool_result.data:
            return None
        child = tool_result.data.get("child_result")
        return child if isinstance(child, dict) else None

    def _lines(self, child: dict[str, object]) -> list[str]:
        payload = json.dumps(child.get("payload", {}), sort_keys=True)
        return [
            f"child_profile: {child.get('profile_id', '')}",
            f"child_status: {child.get('status', '')}",
            f"child_session_id: {child.get('session_id', '')}",
            f"child_summary: {child.get('summary', '')}",
            f"child_payload: {payload}",
        ]
