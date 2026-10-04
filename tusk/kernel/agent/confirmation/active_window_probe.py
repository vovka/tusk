from tusk.kernel.tools.tool_registry import ToolRegistry

__all__ = ["ActiveWindowProbe"]


class ActiveWindowProbe:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def title(self) -> str:
        names = [tool.name for tool in self._registry.all_tools() if tool.name.endswith("get_active_window")]
        if not names:
            return ""
        message = self._registry.get(names[0]).execute({}).message
        # adapter reply format: "active window: <title> -> <application> [...]"
        return message.removeprefix("active window:").split(" -> ")[0].strip()
