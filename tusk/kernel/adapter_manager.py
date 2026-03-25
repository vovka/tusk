import asyncio
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from tusk.kernel.mcp_client import MCPClient
from tusk.kernel.schemas.app_entry import AppEntry
from tusk.kernel.schemas.desktop_context import DesktopContext, WindowInfo
from tusk.kernel.schemas.tool_result import ToolResult

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:  # pragma: no cover
    FileSystemEventHandler = object
    Observer = None

__all__ = ["AdapterManager"]


class AdapterManager:
    def __init__(self, adapters_dir: str, tool_registry: object, log: object, cache_dir: str = ".tusk_runtime/adapters") -> None:
        self.adapters_dir = Path(adapters_dir)
        self.tool_registry = tool_registry
        self._log = log
        self._cache_dir = Path(cache_dir)
        self._clients: dict[str, MCPClient] = {}
        self._manifests: dict[str, dict] = {}
        self._context_adapter: str | None = None
        self._observer = None

    async def start_all(self) -> None:
        if not self.adapters_dir.exists():
            return
        for path in sorted(self.adapters_dir.iterdir()):
            if path.is_dir():
                await self.start_adapter(str(path))

    async def start_adapter(self, adapter_dir: str) -> None:
        path = Path(adapter_dir)
        manifest_path = path / "adapter.json"
        if not manifest_path.exists():
            return
        manifest = json.loads(manifest_path.read_text())
        name = manifest["name"]
        if manifest.get("transport") != "stdio":
            return
        client = await self._connect_stdio(path, manifest)
        tools = await client.list_tools()
        self._clients[name] = client
        self._manifests[name] = manifest
        for tool in tools:
            self.tool_registry.register(_MCPToolProxy(name, tool, client, self.run_async))
        if manifest.get("provides_context") and self._context_adapter is None:
            self._context_adapter = name

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
        handler = _AdapterWatcher(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.adapters_dir), recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def run_async(self, coro: object) -> object:
        return asyncio.run(coro)

    def get_context(self) -> DesktopContext:
        if self._context_adapter is None:
            return DesktopContext("", "")
        result = self.tool_registry.get(f"{self._context_adapter}.get_desktop_context").execute({})
        if not result.success or result.data is None:
            return DesktopContext("", "")
        return DesktopContext(
            active_window_title=result.data.get("active_window_title", ""),
            active_application=result.data.get("active_application", ""),
            open_windows=[WindowInfo(**item) for item in result.data.get("open_windows", [])],
            available_applications=[AppEntry(**item) for item in result.data.get("available_applications", [])],
        )

    def primary_desktop_source(self) -> str:
        return self._context_adapter or "gnome"

    async def _connect_stdio(self, path: Path, manifest: dict) -> MCPClient:
        client = MCPClient()
        command = shlex.split(manifest["entry"])
        try:
            await client.connect_stdio(command, str(path))
            return client
        except Exception:
            env = self._build_fallback_env(path, manifest)
            await client.connect_stdio(command, str(path), env=env)
            return client

    def _build_fallback_env(self, path: Path, manifest: dict) -> dict:
        env = os.environ.copy()
        requirements = path / "requirements.txt"
        if not requirements.exists():
            return env
        cache = self._cache_dir / manifest["name"] / manifest["version"]
        python_bin = cache / "bin" / "python"
        if not python_bin.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, "-m", "venv", str(cache)], check=True)
            subprocess.run([str(python_bin), "-m", "pip", "install", "-r", str(requirements)], check=True)
        env["PATH"] = f"{cache / 'bin'}:{env.get('PATH', '')}"
        env["VIRTUAL_ENV"] = str(cache)
        return env


class _MCPToolProxy:
    def __init__(self, source: str, schema: object, client: MCPClient, runner: object) -> None:
        self.name = f"{source}.{schema.name}"
        self.description = schema.description
        self.input_schema = schema.input_schema
        self.source = source
        self._tool_name = schema.name
        self._client = client
        self._runner = runner

    def execute(self, parameters: dict) -> ToolResult:
        result = self._runner(self._client.call_tool(self._tool_name, parameters))
        return ToolResult(not result.is_error, result.content, result.data)


class _AdapterWatcher(FileSystemEventHandler):
    def __init__(self, manager: AdapterManager) -> None:
        self._manager = manager

    def on_created(self, event) -> None:
        if not event.is_directory:
            return
        self._manager.run_async(self._manager.start_adapter(event.src_path))
