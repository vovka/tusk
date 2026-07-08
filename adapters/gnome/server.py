import sys
from typing import TextIO

from adapters.gnome.app_catalog import AppCatalog
from adapters.gnome.gnome_clipboard_provider import GnomeClipboardProvider
from adapters.gnome.gnome_context_provider import GnomeContextProvider
from adapters.gnome.gnome_input_simulator import GnomeInputSimulator
from adapters.gnome.gnome_text_paster import GnomeTextPaster
from adapters.gnome.gnome_tool_router import GnomeToolRouter
from tusk.shared.mcp.mcp_stdio_server import MCPStdioServer

__all__ = ["build_router", "build_server"]


def build_router() -> GnomeToolRouter:
    apps = AppCatalog()
    context = GnomeContextProvider(apps)
    return GnomeToolRouter(apps, GnomeClipboardProvider(), context, GnomeInputSimulator(), GnomeTextPaster())


def build_server(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> MCPStdioServer:
    router = build_router()
    return MCPStdioServer("gnome", lambda: list(router.schemas().values()), router.call, input_stream, output_stream)


def main() -> None:
    build_server().serve()


if __name__ == "__main__":
    main()
