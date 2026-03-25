import json

from tusk.kernel.tool_usage_store import ToolUsageStore


def test_tool_usage_store_tracks_successful_usage(tmp_path) -> None:
    store = ToolUsageStore(tmp_path / "tool_usage.json", lambda: 1000.0)
    store.record_success("gnome.type_text")
    assert "gnome.type_text" in json.loads((tmp_path / "tool_usage.json").read_text())


def test_tool_usage_store_returns_recent_top_names(tmp_path) -> None:
    store = ToolUsageStore(tmp_path / "tool_usage.json", lambda: 2000.0)
    _write_usage(tmp_path, "gnome.type_text", 5.0, 1)
    _write_usage(tmp_path, "gnome.press_keys", 2.0, 1999)
    assert store.top_tool_names({"gnome.type_text", "gnome.press_keys"})[0] == "gnome.press_keys"


def test_tool_usage_store_handles_malformed_file(tmp_path) -> None:
    path = tmp_path / "tool_usage.json"
    path.write_text("{oops")
    assert ToolUsageStore(path, lambda: 1000.0).top_tool_names({"gnome.type_text"}) == []


def _write_usage(tmp_path, name: str, score: float, last_used_at: int) -> None:
    path = tmp_path / "tool_usage.json"
    path.write_text(json.dumps({name: {"score": score, "count": 1, "last_used_at": last_used_at}}))
