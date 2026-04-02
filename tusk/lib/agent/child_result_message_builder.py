import json

from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["ChildResultMessageBuilder"]


class ChildResultMessageBuilder:
    def build(self, tool_result: ToolResult) -> str | None:
        child = self._child_result(tool_result)
        if child is None:
            return None
        payload = json.dumps(child.get("payload", {}), sort_keys=True)
        return "\n".join([
            "[child-result]",
            f"child_profile: {child.get('profile_id', '')}",
            f"child_status: {child.get('status', '')}",
            f"child_session_id: {child.get('session_id', '')}",
            f"child_summary: {child.get('summary', '')}",
            f"child_payload: {payload}",
        ])

    def _child_result(self, tool_result: ToolResult) -> dict[str, object] | None:
        if not tool_result.data:
            return None
        child = tool_result.data.get("child_result")
        return child if isinstance(child, dict) else None
