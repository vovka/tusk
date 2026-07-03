import json
from pathlib import Path

from tools.codex_mcp_config_generator import CodexMcpConfigGenerator


def _write_adapter(root: Path, name: str, transport: str = "stdio") -> None:
    directory = root / name
    directory.mkdir(parents=True)
    manifest = {"name": name, "transport": transport, "entry": "python server.py"}
    (directory / "adapter.json").write_text(json.dumps(manifest))


def test_generates_one_section_per_stdio_adapter(tmp_path: Path) -> None:
    _write_adapter(tmp_path, "gnome")
    _write_adapter(tmp_path, "dictation")

    output = CodexMcpConfigGenerator(tmp_path, {"DISPLAY": ":1"}).generate()

    assert '[mcp_servers."dictation"]' in output
    assert '[mcp_servers."gnome"]' in output


def test_section_contains_command_script_and_env(tmp_path: Path) -> None:
    _write_adapter(tmp_path, "gnome")

    output = CodexMcpConfigGenerator(tmp_path, {"DISPLAY": ":1"}).generate()

    assert 'command = "python3"' in output
    assert f'args = ["{tmp_path}/gnome/server.py"]' in output
    assert f'PYTHONPATH = "{tmp_path}/gnome"' in output
    assert 'DISPLAY = ":1"' in output


def test_skips_non_stdio_adapters(tmp_path: Path) -> None:
    _write_adapter(tmp_path, "gnome")
    _write_adapter(tmp_path, "web", transport="http")

    output = CodexMcpConfigGenerator(tmp_path, {}).generate()

    assert "web" not in output
    assert '[mcp_servers."gnome"]' in output
