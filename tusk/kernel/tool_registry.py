from tusk.kernel.registered_tool import RegisteredTool
from tusk.kernel.tool_prompt_builder import ToolPromptBuilder
from tusk.kernel.visible_tool_definition_builder import VisibleToolDefinitionBuilder

__all__ = ["ToolRegistry"]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._prompt_builder = ToolPromptBuilder()
        self._definition_builder = VisibleToolDefinitionBuilder()

    def register(self, tool: object) -> None:
        entry = self._entry(tool)
        self._tools[entry.name] = entry

    def unregister_source(self, source: str) -> None:
        names = [name for name, tool in self._tools.items() if tool.source == source]
        for name in names:
            self._tools.pop(name, None)

    def get(self, name: str) -> RegisteredTool:
        return self._tools[name]

    def all_tools(self) -> list[RegisteredTool]:
        return list(self._tools.values())

    def real_tools(self) -> list[RegisteredTool]:
        return sorted(self._tools.values(), key=lambda item: item.name)

    def real_tool_names(self) -> set[str]:
        return {tool.name for tool in self.real_tools()}

    def planner_tool_names(self) -> set[str]:
        return {tool.name for tool in self.planner_tools()}

    def build_planner_catalog_text(self) -> str:
        return self._prompt_builder.build(self.planner_tools())

    def definitions_for(self, names: set[str]) -> list[dict[str, object]]:
        tools = [self._tools[name] for name in sorted(names) if name in self._tools]
        return self._definition_builder.build(tools)

    def planner_tools(self) -> list[RegisteredTool]:
        return [tool for tool in self.real_tools() if tool.planner_visible]

    def _entry(self, tool: object) -> RegisteredTool:
        return RegisteredTool(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            execute=tool.execute,
            source=getattr(tool, "source", "kernel"),
            planner_visible=getattr(tool, "planner_visible", True),
        )
