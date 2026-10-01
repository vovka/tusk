import re

__all__ = ["DestructiveActionPolicy"]

_DESTRUCTIVE_TOOL_PREFIXES = ("kill", "delete", "run_shell", "execute_shell", "shell")
# press_keys has no target argument, so any deleting/closing key acts on whatever window has focus;
# ctrl+a alone only selects, the Delete/BackSpace that follows is what destroys.
_DELETING_KEYS = ("delete", "backspace")
_CLOSING_COMBOS = ({"alt", "f4"}, {"ctrl", "w"}, {"ctrl", "q"})


class DestructiveActionPolicy:
    def describe(self, tool_name: str, arguments: dict[str, object]) -> str | None:
        base_name = tool_name.rsplit(".", 1)[-1]
        if base_name == "close_window":
            return "Close window"
        if base_name == "press_keys":
            return self._describe_keys(str(arguments.get("keys", "")))
        if base_name.startswith(_DESTRUCTIVE_TOOL_PREFIXES):
            return f"Run {base_name} in window"
        return None

    def _describe_keys(self, keys: str) -> str | None:
        # models spell combos both as "<ctrl>w" and "Ctrl+W", so compare key names, not the raw string
        pressed = set(re.split(r"[+<>\s]+", keys.lower().replace("control", "ctrl"))) - {""}
        deleting = any(name in key for key in pressed for name in _DELETING_KEYS)
        if deleting or any(combo <= pressed for combo in _CLOSING_COMBOS):
            return f"Press {keys} in window"
        return None
