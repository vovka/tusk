from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult
import json
from tusk.kernel.agent.session.store import Store
from tusk.kernel.tools.tool_registry import ToolRegistry

__all__ = ["StepRecorder"]


class StepRecorder:
    def __init__(self, session_store: Store, tool_registry: ToolRegistry) -> None:
        self._store = session_store
        self._registry = tool_registry

    def append_message(self, session_id: str, role: str, content: str) -> None:
        self._store.append_event(session_id, "message_appended", {"role": role, "content": content})

    def requested(self, session_id: str, step: int, tool_call: ToolCall) -> None:
        data = {"step": step, "tool_name": tool_call.tool_name, "parameters": tool_call.parameters}
        self._store.append_event(session_id, "tool_call_requested", data)

    def result(self, session_id: str, step: int, tool_call: ToolCall, tool_result: ToolResult) -> None:
        data = {"step": step, "tool_name": tool_call.tool_name, "success": tool_result.success, "message": tool_result.message}
        if tool_result.data:
            data["data"] = tool_result.data
        self._store.append_event(session_id, "tool_call_result", data)

    def appended(self, messages: list[dict[str, str]], tool_call: ToolCall, tool_result: ToolResult) -> None:
        messages.append({"role": "assistant", "content": f"[tool:{tool_call.tool_name}] called"})
        child = _child_result_message(tool_result)
        if child is not None:
            messages.append({"role": "assistant", "content": child})
            return
        messages.append({"role": "user", "content": self._user_message(tool_call, tool_result)})
        clipboard = _clipboard_message(tool_call, tool_result)
        if clipboard is not None:
            messages.append({"role": "assistant", "content": clipboard})

    def _user_message(self, tool_call: ToolCall, tool_result: ToolResult) -> str:
        message = _transcript_message(tool_result)
        if tool_result.success and self._is_actuator(tool_call.tool_name):
            return message + _DONE_NUDGE
        return message

    def _is_actuator(self, tool_name: str) -> bool:
        # Only actuators (sequence_callable) finish a command; read-only probes must keep probing.
        return tool_name in self._registry.sequence_tool_names()


_MESSAGE_LIMIT_CHARS = 500

_DONE_NUDGE = " Call the done tool now if the command is complete."


def _transcript_message(tool_result: ToolResult) -> str:
    message = tool_result.message or ""
    # ponytail: only failed-step spam is capped — successful messages can be data (e.g. clipboard reads)
    return message if tool_result.success else _truncated(message)


def _truncated(text: str) -> str:
    # only the in-run LLM transcript is capped; store events keep the full message
    if len(text) <= _MESSAGE_LIMIT_CHARS:
        return text
    return text[:_MESSAGE_LIMIT_CHARS] + "…[truncated]"


def _child_result_message(tool_result: ToolResult) -> str | None:
    child = tool_result.data.get("child_result") if isinstance(tool_result.data, dict) else None
    if not isinstance(child, dict):
        return None
    return "\n".join(["[child-result]", *_child_result_lines(child)])


def _child_result_lines(child: dict[str, object]) -> list[str]:
    payload = json.dumps(child.get("payload", {}), sort_keys=True)
    return [
        f"child_profile: {child.get('profile_id', '')}",
        f"child_status: {child.get('status', '')}",
        f"child_session_id: {child.get('session_id', '')}",
        f"child_summary: {child.get('summary', '')}",
        f"child_payload: {payload}",
    ]


def _clipboard_message(tool_call: ToolCall, tool_result: ToolResult) -> str | None:
    if tool_call.tool_name != "gnome.write_clipboard" or not isinstance(tool_result.data, dict):
        return None
    text = tool_result.data.get("clipboard_text")
    return f"[clipboard-written]\n{text}" if isinstance(text, str) else None
