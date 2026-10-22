from tusk.kernel.tools.registered_tool import RegisteredTool

__all__ = ["ToolRegistry"]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: object) -> None:
        entry = self._entry(tool)
        self._tools[entry.name] = entry

    def get(self, name: str) -> RegisteredTool:
        return self._tools[name]

    def resolve_name(self, name: str) -> str:
        # models drop the adapter prefix ("switch_workspace"); a unique suffix match saves a whole LLM retry hop
        if name in self._tools:
            return name
        matches = [full for full in self._tools if full.endswith(f".{name}")]
        return matches[0] if len(matches) == 1 else name

    def all_tools(self) -> list[RegisteredTool]:
        return sorted(self._tools.values(), key=lambda item: item.name)

    def tool_names(self) -> set[str]:
        return set(self._tools)

    def planner_tools(self) -> list[RegisteredTool]:
        return [tool for tool in self.all_tools() if tool.planner_visible]

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
            sequence_callable=getattr(tool, "sequence_callable", False),
            settle_ms=getattr(tool, "settle_ms", 0),
        )
