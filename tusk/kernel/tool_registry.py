import json

from tusk.kernel.registered_tool import RegisteredTool

__all__ = ["ToolRegistry"]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: object) -> None:
        entry = RegisteredTool(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            execute=tool.execute,
            source=getattr(tool, "source", "kernel"),
        )
        self._tools[entry.name] = entry

    def unregister_source(self, source: str) -> None:
        names = [name for name, tool in self._tools.items() if tool.source == source]
        for name in names:
            self._tools.pop(name, None)

    def get(self, name: str) -> RegisteredTool:
        return self._tools[name]

    def all_tools(self) -> list[RegisteredTool]:
        return list(self._tools.values())

    def build_schema_text(self) -> str:
        return "\n\n".join(self._schema_lines(tool) for tool in self._tools.values())

    def _schema_lines(self, tool: RegisteredTool) -> str:
        return "\n".join([
            f"Tool: {tool.name}",
            f"Description: {tool.description}",
            f"Parameters: {json.dumps(tool.input_schema, sort_keys=True)}",
        ])
