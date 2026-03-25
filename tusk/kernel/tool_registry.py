from tusk.kernel.registered_tool import RegisteredTool
from tusk.kernel.tool_prompt_builder import ToolPromptBuilder
from tusk.kernel.visible_tool_definition_builder import VisibleToolDefinitionBuilder

__all__ = ["ToolRegistry"]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._broker_tools: set[str] = set()
        self._prompt_visible: set[str] = set()
        self._prompt_builder = ToolPromptBuilder()
        self._definition_builder = VisibleToolDefinitionBuilder()

    def register(self, tool: object) -> None:
        entry = self._entry(tool)
        self._tools[entry.name] = entry
        self._remember_flags(tool, entry.name)

    def unregister_source(self, source: str) -> None:
        names = [name for name, tool in self._tools.items() if tool.source == source]
        for name in names:
            self._tools.pop(name, None)
            self._broker_tools.discard(name)
            self._prompt_visible.discard(name)

    def get(self, name: str) -> RegisteredTool:
        return self._tools[name]

    def all_tools(self) -> list[RegisteredTool]:
        return list(self._tools.values())

    def real_tools(self) -> list[RegisteredTool]:
        return [tool for tool in self._tools.values() if tool.name not in self._broker_tools]

    def real_tool_names(self) -> set[str]:
        return {tool.name for tool in self.real_tools()}

    def build_prompt_text(self) -> str:
        return self._prompt_builder.build(self.real_tools())

    def visible_tool_definitions(self, described: set[str] | None = None) -> list[dict[str, object]]:
        return self._definition_builder.build(self._callable_tools(described or set()))

    def visible_tools(self) -> list[RegisteredTool]:
        names = [name for name in self._tools if name in self._prompt_visible]
        return sorted((self._tools[name] for name in names), key=self._visible_key)

    def can_call_directly(self, name: str) -> bool:
        return name in self._broker_tools

    def can_call_described(self, name: str, described: set[str]) -> bool:
        return name in self._broker_tools or name in described

    def is_broker(self, name: str) -> bool:
        return name in self._broker_tools

    def mark_prompt_visible(self, names: list[str]) -> None:
        self._prompt_visible.update(name for name in names if name in self._tools)

    def _visible_key(self, tool: RegisteredTool) -> tuple[bool, str]:
        return tool.name not in self._broker_tools, tool.name

    def _callable_tools(self, described: set[str]) -> list[RegisteredTool]:
        names = [name for name in self._tools if self._callable(name, described)]
        return sorted((self._tools[name] for name in names), key=self._visible_key)

    def _callable(self, name: str, described: set[str]) -> bool:
        return name in self._broker_tools or name in described

    def _entry(self, tool: object) -> RegisteredTool:
        return RegisteredTool(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            execute=tool.execute,
            source=getattr(tool, "source", "kernel"),
        )

    def _remember_flags(self, tool: object, name: str) -> None:
        if getattr(tool, "broker", False):
            self._broker_tools.add(name)
        if getattr(tool, "prompt_visible", False):
            self._prompt_visible.add(name)
