__all__ = ["FindToolsTool"]


class FindToolsTool:
    source = "kernel"
    broker = True
    prompt_visible = True
    name = "find_tools"
    description = "Find relevant tools for a task"
    input_schema = {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}}

    def __init__(self, tool_registry: object) -> None:
        self._registry = tool_registry

    def execute(self, parameters: dict) -> object:
        query = str(parameters.get("query", "")).strip()
        if not query:
            return self._result(False, "find_tools requires a non-empty query")
        return self._result(True, self._message(query, self._matches(query, parameters)))

    def _matches(self, query: str, parameters: dict) -> list[object]:
        limit = int(parameters.get("limit", 5))
        scored = [(self._score(tool, query), tool) for tool in self._registry.real_tools()]
        return [tool for score, tool in sorted(scored, key=lambda item: (-item[0], item[1].name)) if score > 0][:limit]

    def _message(self, query: str, matches: list[object]) -> str:
        lines = [self._line(tool) for tool in matches]
        return f"tool matches for {query!r}:\n" + ("\n".join(lines) if lines else "none")

    def _score(self, tool: object, query: str) -> int:
        haystack = " ".join(self._terms(tool)).lower()
        return sum(1 for term in query.lower().split() if term in haystack)

    def _result(self, success: bool, message: str) -> object:
        from tusk.kernel.schemas.tool_result import ToolResult

        return ToolResult(success, message)

    def _line(self, tool: object) -> str:
        fields = ", ".join(tool.input_schema.get("properties", {}).keys())
        return f"{tool.name}({fields}): {tool.description}"

    def _terms(self, tool: object) -> list[str]:
        names = list(tool.input_schema.get("properties", {}).keys())
        return [tool.name.replace(".", " ").replace("_", " "), tool.description, *names]
