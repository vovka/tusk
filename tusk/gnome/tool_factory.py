from tusk.core.llm_registry import LLMRegistry
from tusk.core.tool_registry import ToolRegistry
from tusk.gnome.tools.ai_transform_tool import AiTransformTool
from tusk.gnome.tools.close_window_tool import CloseWindowTool
from tusk.gnome.tools.focus_window_tool import FocusWindowTool
from tusk.gnome.tools.launch_application_tool import LaunchApplicationTool
from tusk.gnome.tools.maximize_window_tool import MaximizeWindowTool
from tusk.gnome.tools.minimize_window_tool import MinimizeWindowTool
from tusk.gnome.tools.mouse_click_tool import MouseClickTool
from tusk.gnome.tools.mouse_drag_tool import MouseDragTool
from tusk.gnome.tools.mouse_move_tool import MouseMoveTool
from tusk.gnome.tools.mouse_scroll_tool import MouseScrollTool
from tusk.gnome.tools.move_resize_window_tool import MoveResizeWindowTool
from tusk.gnome.tools.open_uri_tool import OpenUriTool
from tusk.gnome.tools.press_keys_tool import PressKeysTool
from tusk.gnome.tools.read_clipboard_tool import ReadClipboardTool
from tusk.gnome.tools.switch_model_tool import SwitchModelTool
from tusk.gnome.tools.switch_workspace_tool import SwitchWorkspaceTool
from tusk.gnome.tools.type_text_tool import TypeTextTool
from tusk.gnome.tools.write_clipboard_tool import WriteClipboardTool
from tusk.interfaces.clipboard_provider import ClipboardProvider
from tusk.interfaces.input_simulator import InputSimulator
from tusk.interfaces.llm_provider import LLMProvider

__all__ = ["build_tool_registry"]

_SOCKET_PATH = "/tmp/tusk/launch.sock"


def build_tool_registry(
    simulator: InputSimulator,
    clipboard: ClipboardProvider,
    utility_llm: LLMProvider,
    llm_registry: LLMRegistry,
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(LaunchApplicationTool(_SOCKET_PATH))
    registry.register(CloseWindowTool())
    _register_input_tools(registry, simulator)
    _register_window_tools(registry)
    _register_mouse_tools(registry, simulator)
    _register_clipboard_tools(registry, clipboard)
    _register_desktop_tools(registry)
    registry.register(AiTransformTool(simulator, clipboard, utility_llm))
    registry.register(SwitchModelTool(llm_registry))
    return registry


def _register_input_tools(registry: ToolRegistry, simulator: InputSimulator) -> None:
    registry.register(PressKeysTool(simulator))
    registry.register(TypeTextTool(simulator))


def _register_window_tools(registry: ToolRegistry) -> None:
    registry.register(FocusWindowTool())
    registry.register(MaximizeWindowTool())
    registry.register(MinimizeWindowTool())
    registry.register(MoveResizeWindowTool())


def _register_mouse_tools(registry: ToolRegistry, simulator: InputSimulator) -> None:
    registry.register(MouseClickTool(simulator))
    registry.register(MouseMoveTool(simulator))
    registry.register(MouseDragTool(simulator))
    registry.register(MouseScrollTool(simulator))


def _register_clipboard_tools(registry: ToolRegistry, clipboard: ClipboardProvider) -> None:
    registry.register(ReadClipboardTool(clipboard))
    registry.register(WriteClipboardTool(clipboard))


def _register_desktop_tools(registry: ToolRegistry) -> None:
    registry.register(OpenUriTool())
    registry.register(SwitchWorkspaceTool())
