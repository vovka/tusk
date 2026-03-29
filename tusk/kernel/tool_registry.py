from tusk.kernel.registered_tool import RegisteredTool

__all__ = ["ToolRegistry"]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

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

    def planner_tools(self) -> list[RegisteredTool]:
        return [tool for tool in self.real_tools() if tool.planner_visible]

    def definitions_for(self, names: set[str]) -> list[dict[str, object]]:
        tools = [self._tools[name] for name in sorted(names) if name in self._tools]
        return [self._definition(tool) for tool in tools]

    def _definition(self, tool: RegisteredTool) -> dict[str, object]:
        return {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema}}

    def _entry(self, tool: object) -> RegisteredTool:
        return RegisteredTool(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            execute=tool.execute,
            source=getattr(tool, "source", "kernel"),
            planner_visible=getattr(tool, "planner_visible", True),
        )
