import os
import sys
from typing import TextIO

from adapters.gnome.app_catalog import AppCatalog
from adapters.gnome.gnome_clipboard_provider import GnomeClipboardProvider
from adapters.gnome.gnome_tool_router import GnomeToolRouter
from adapters.gnome.wayland.shell_bus import ShellBus
from adapters.gnome.wayland.wayland_context_provider import WaylandContextProvider
from adapters.gnome.wayland.wayland_input_simulator import WaylandInputSimulator
from adapters.gnome.wayland.wayland_window_tools import WaylandWindowTools
from adapters.gnome.x11.context_provider import X11ContextProvider
from adapters.gnome.x11.input_simulator import X11InputSimulator
from adapters.gnome.x11.window_tools import WindowTools
from adapters.gnome.x11.windows import X11Windows
from tusk.shared.mcp.mcp_stdio_server import MCPStdioServer

__all__ = ["build_router", "build_server"]


def build_router() -> GnomeToolRouter:
    apps = AppCatalog()
    if os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY"):
        return _wayland_router(apps, ShellBus())
    context = X11ContextProvider(apps)
    return GnomeToolRouter(apps, GnomeClipboardProvider(), context, X11InputSimulator(), WindowTools(), X11Windows())


def _wayland_router(apps: AppCatalog, bus: ShellBus) -> GnomeToolRouter:
    context = WaylandContextProvider(apps, bus)
    # The Wayland window tools also list and focus windows by id, so they fill both window roles.
    windows = WaylandWindowTools(bus)
    return GnomeToolRouter(apps, GnomeClipboardProvider(), context, WaylandInputSimulator(bus), windows, windows)


def build_server(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> MCPStdioServer:
    router = build_router()
    return MCPStdioServer("gnome", lambda: list(router.schemas().values()), router.call, input_stream, output_stream)


def main() -> None:
    build_server().serve()


if __name__ == "__main__":
    main()
