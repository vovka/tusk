import json
import types
from pathlib import Path

from tusk.kernel.core.adapter_manager import AdapterManager

_GNOME_SEQUENCE_TOOLS = {
    "close_window", "focus_window", "maximize_window", "minimize_window",
    "move_resize_window", "switch_workspace", "press_keys", "type_text",
    "replace_recent_text", "mouse_click", "mouse_move", "mouse_drag",
    "mouse_scroll", "write_clipboard",
}


def _tool_flags(adapter: str) -> dict:
    manifest = json.loads(Path(f"adapters/{adapter}/adapter.json").read_text())
    return manifest.get("tools", {})


def test_gnome_manifest_marks_sequence_callable_tools() -> None:
    flags = _tool_flags("gnome")
    marked = {name for name, entry in flags.items() if entry.get("sequence_callable")}
    assert marked == _GNOME_SEQUENCE_TOOLS


def test_dictation_manifest_hides_lifecycle_tools() -> None:
    flags = _tool_flags("dictation")
    hidden = {name for name, entry in flags.items() if entry.get("planner_visible") is False}
    assert hidden == {"start_dictation", "stop_dictation"}


def test_coding_manifest_hides_lifecycle_tools() -> None:
    flags = _tool_flags("coding")
    hidden = {name for name, entry in flags.items() if entry.get("planner_visible") is False}
    assert hidden == {"start_coding_session", "process_intent", "stop_coding_session"}


def test_register_passes_manifest_flags_to_proxies() -> None:
    registered: list[object] = []
    registry = types.SimpleNamespace(register=registered.append)
    manager = AdapterManager("adapters", registry, types.SimpleNamespace(log=lambda *a: None))
    manifest = {"name": "demo", "tools": {"hidden_tool": {"planner_visible": False, "sequence_callable": True}}}
    schemas = [_schema("hidden_tool"), _schema("normal_tool")]
    manager._register("demo", types.SimpleNamespace(), manifest, schemas)
    flags = {tool.name: (tool.planner_visible, tool.sequence_callable) for tool in registered}
    assert flags == {"demo.hidden_tool": (False, True), "demo.normal_tool": (True, False)}


def _schema(name: str) -> object:
    return types.SimpleNamespace(name=name, description="", input_schema={})
