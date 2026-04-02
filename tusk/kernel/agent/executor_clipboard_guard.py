from tusk.shared.schemas.tool_call import ToolCall
from tusk.shared.schemas.tool_result import ToolResult

__all__ = ["ExecutorClipboardGuard"]


class ExecutorClipboardGuard:
    def __init__(self) -> None:
        self._dirty = False
        self._text = ""

    def violation(self, profile_id: str, tool_call: ToolCall) -> str | None:
        if profile_id != "executor" or not self._dirty or tool_call.tool_name == "done":
            return None
        if tool_call.tool_name == "gnome.write_clipboard":
            return self._write_violation(tool_call)
        if self._is_copy(tool_call):
            return "executor must not copy to clipboard again before paste"
        return None

    def observe(self, tool_call: ToolCall, tool_result: ToolResult) -> None:
        if not tool_result.success:
            return
        if tool_call.tool_name == "gnome.write_clipboard":
            self._mark_dirty(str(tool_call.parameters.get("text", "")))
            return
        if self._is_copy(tool_call):
            self._mark_dirty("")
            return
        if self._is_paste(tool_call):
            self._reset()

    def _write_violation(self, tool_call: ToolCall) -> str:
        text = str(tool_call.parameters.get("text", ""))
        if self._text and text != self._text:
            return "executor must not change clipboard text before paste"
        return "executor must not copy to clipboard again before paste"

    def _is_copy(self, tool_call: ToolCall) -> bool:
        if tool_call.tool_name != "gnome.press_keys":
            return False
        keys = str(tool_call.parameters.get("keys", "")).lower().replace(" ", "")
        return keys in {"<ctrl>c", "ctrl+c", "ctrlc", "<meta>c", "meta+c", "metac", "<ctrl><shift>c", "ctrl+shift+c", "ctrlshiftc"}

    def _is_paste(self, tool_call: ToolCall) -> bool:
        if tool_call.tool_name != "gnome.press_keys":
            return False
        keys = str(tool_call.parameters.get("keys", "")).lower().replace(" ", "")
        return keys in {"<ctrl>v", "ctrl+v", "ctrlv", "<meta>v", "meta+v", "metav", "<ctrl><shift>v", "ctrl+shift+v", "ctrlshiftv", "shift+insert", "shiftinsert"}

    def _reset(self) -> None:
        self._dirty = False
        self._text = ""

    def _mark_dirty(self, text: str) -> None:
        self._dirty = True
        self._text = text
