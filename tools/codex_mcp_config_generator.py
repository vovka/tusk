# Emits codex `mcp_servers` TOML sections from the same adapters/*/adapter.json
# manifests TUSK loads, so codex always sees the same adapter set.
# Usage (codex-entrypoint.sh): python3 tools/codex_mcp_config_generator.py /app/adapters
import json
import os
import sys
from pathlib import Path

__all__ = ["CodexMcpConfigGenerator"]


class CodexMcpConfigGenerator:
    def __init__(self, adapters_dir: Path, server_env: dict[str, str]) -> None:
        self._adapters_dir = adapters_dir
        self._server_env = server_env

    def generate(self) -> str:
        sections = [self._section(path) for path in sorted(self._adapters_dir.glob("*/adapter.json"))]
        return "\n".join(section for section in sections if section)

    def _section(self, manifest_path: Path) -> str:
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("transport") != "stdio":
            return ""
        return self._toml(manifest["name"], manifest_path.parent / self._script(manifest))

    def _script(self, manifest: dict) -> str:
        return manifest["entry"].split()[-1]

    def _toml(self, name: str, script: Path) -> str:
        env = {"PYTHONPATH": str(script.parent), **self._server_env}
        env_items = ", ".join(f"{key} = {json.dumps(value)}" for key, value in env.items())
        return (
            f'[mcp_servers."{name}"]\n'
            f'command = "python3"\n'
            f"args = [{json.dumps(str(script))}]\n"
            f"env = {{ {env_items} }}\n"
        )


def main() -> None:
    display_env = {key: os.environ.get(key, "") for key in ("DISPLAY", "XAUTHORITY")}
    server_env = {key: value for key, value in display_env.items() if value}
    print(CodexMcpConfigGenerator(Path(sys.argv[1]), server_env).generate())


if __name__ == "__main__":
    main()
