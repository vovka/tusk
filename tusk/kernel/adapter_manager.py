import json
import shlex
from pathlib import Path

from tusk.shared.mcp import AdapterEnvironmentBuilder, AdapterWatcher, MCPClient, MCPToolProxy
from tusk.kernel.tool_registry import ToolRegistry
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.mcp_tool_schema import MCPToolSchema

try:
    from watchdog.observers import Observer
except ImportError:  # pragma: no cover
    Observer = None

__all__ = ["AdapterManager"]


class AdapterManager:
    def __init__(self, adapters_dir: str, tool_registry: ToolRegistry, log: LogPrinter, cache_dir: str = ".tusk_runtime/adapters") -> None:
        self.adapters_dir = Path(adapters_dir)
        self.tool_registry = tool_registry
        self._log = log
        self._clients: dict[str, MCPClient] = {}
        self._manifests: dict[str, dict] = {}
        self._context_adapter: str | None = None
        self._observer = None
        self._env_builder = AdapterEnvironmentBuilder(cache_dir)

    def start_all(self) -> None:
        if not self.adapters_dir.exists():
            return
        for path in sorted(self.adapters_dir.iterdir()):
            if path.is_dir():
                self.start_adapter(str(path))

    def start_adapter(self, adapter_dir: str) -> None:
        path = Path(adapter_dir)
        manifest = self._manifest(path)
        if manifest is None:
            return
        name = manifest["name"]
        if manifest.get("transport") != "stdio":
            return
        client = self._connect_stdio(path, manifest)
        self._register(name, client, manifest, client.list_tools())

    def stop_adapter(self, name: str) -> None:
        client = self._clients.pop(name, None)
        if client is not None:
            client.shutdown()
        self.tool_registry.unregister_source(name)
        if self._context_adapter == name:
            self._context_adapter = None

    def stop_all(self) -> None:
        for name in list(self._clients):
            self.stop_adapter(name)

    def start_watcher(self) -> None:
        if Observer is None:
            self._log.log("PIPELINE", "watchdog not installed; adapter hot-plug disabled")
            return
        self._observer = Observer()
        self._observer.schedule(AdapterWatcher(self), str(self.adapters_dir), recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def primary_desktop_source(self) -> str:
        return self._context_adapter or "gnome"

    def _connect_stdio(self, path: Path, manifest: dict) -> MCPClient:
        client = MCPClient()
        command = shlex.split(manifest["entry"])
        try:
            client.connect_stdio(command, str(path), env=self._env_builder.base_env())
            return client
        except Exception:
            env = self._env_builder.build(path, manifest)
            client.connect_stdio(command, str(path), env=env)
            return client

    def _manifest(self, path: Path) -> dict | None:
        manifest_path = path / "adapter.json"
        return json.loads(manifest_path.read_text()) if manifest_path.exists() else None

    def _register(self, name: str, client: MCPClient, manifest: dict, tools: list[object]) -> None:
        self._clients[name] = client
        self._manifests[name] = manifest
        tool_flags = manifest.get("tools", {})
        for tool in tools:
            self.tool_registry.register(self._proxy(name, tool, client, tool_flags.get(tool.name, {})))
        if manifest.get("provides_context") and self._context_adapter is None:
            self._context_adapter = name

    def _proxy(self, name: str, tool: MCPToolSchema, client: MCPClient, flags: dict) -> MCPToolProxy:
        return MCPToolProxy(
            name, tool, client,
            planner_visible=flags.get("planner_visible", True),
            sequence_callable=flags.get("sequence_callable", False),
        )
