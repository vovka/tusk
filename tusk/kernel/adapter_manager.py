import asyncio
import json
import shlex
from pathlib import Path

from tusk.kernel.adapter_context_builder import AdapterContextBuilder
from tusk.kernel.adapter_env_builder import AdapterEnvironmentBuilder
from tusk.kernel.adapter_watcher import AdapterWatcher
from tusk.kernel.mcp_client import MCPClient
from tusk.kernel.mcp_tool_proxy import MCPToolProxy
from tusk.kernel.schemas.desktop_context import DesktopContext

try:
    from watchdog.observers import Observer
except ImportError:  # pragma: no cover
    Observer = None

__all__ = ["AdapterManager"]


class AdapterManager:
    def __init__(self, adapters_dir: str, tool_registry: object, log: object, cache_dir: str = ".tusk_runtime/adapters") -> None:
        self.adapters_dir = Path(adapters_dir)
        self.tool_registry = tool_registry
        self._log = log
        self._clients: dict[str, MCPClient] = {}
        self._manifests: dict[str, dict] = {}
        self._context_adapter: str | None = None
        self._observer = None
        self._context_builder = AdapterContextBuilder()
        self._env_builder = AdapterEnvironmentBuilder(cache_dir)

    async def start_all(self) -> None:
        if not self.adapters_dir.exists():
            return
        for path in sorted(self.adapters_dir.iterdir()):
            if path.is_dir():
                await self.start_adapter(str(path))

    async def start_adapter(self, adapter_dir: str) -> None:
        path = Path(adapter_dir)
        manifest = self._manifest(path)
        if manifest is None:
            return
        name = manifest["name"]
        if manifest.get("transport") != "stdio":
            return
        client = await self._connect_stdio(path, manifest)
        self._register(name, client, manifest, await client.list_tools())

    async def stop_adapter(self, name: str) -> None:
        client = self._clients.pop(name, None)
        if client is not None:
            await client.shutdown()
        self.tool_registry.unregister_source(name)
        if self._context_adapter == name:
            self._context_adapter = None

    async def stop_all(self) -> None:
        for name in list(self._clients):
            await self.stop_adapter(name)

    def start_watcher(self) -> None:
        if Observer is None:
            self._log.log("PIPELINE", "watchdog not installed; adapter hot-plug disabled")
            return
        self._observer = Observer()
        self._observer.schedule(AdapterWatcher(self), str(self.adapters_dir), recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def run_async(self, coro: object) -> object:
        return asyncio.run(coro)

    def get_context(self) -> DesktopContext:
        if self._context_adapter is None:
            return self._context_builder.build(None)
        return self._context_builder.build(self._context_result())

    def primary_desktop_source(self) -> str:
        return self._context_adapter or "gnome"

    async def _connect_stdio(self, path: Path, manifest: dict) -> MCPClient:
        client = MCPClient()
        command = shlex.split(manifest["entry"])
        try:
            await client.connect_stdio(command, str(path))
            return client
        except Exception:
            env = self._env_builder.build(path, manifest)
            await client.connect_stdio(command, str(path), env=env)
            return client

    def _manifest(self, path: Path) -> dict | None:
        manifest_path = path / "adapter.json"
        return json.loads(manifest_path.read_text()) if manifest_path.exists() else None

    def _register(self, name: str, client: MCPClient, manifest: dict, tools: list[object]) -> None:
        self._clients[name] = client
        self._manifests[name] = manifest
        for tool in tools:
            self.tool_registry.register(MCPToolProxy(name, tool, client, self.run_async))
        if manifest.get("provides_context") and self._context_adapter is None:
            self._context_adapter = name

    def _context_result(self) -> dict | None:
        name = f"{self._context_adapter}.get_desktop_context"
        result = self.tool_registry.get(name).execute({})
        return result.data if result.success else None
