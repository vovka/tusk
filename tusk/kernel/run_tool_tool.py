from tusk.kernel.tool_input_json_parser import ToolInputJsonParser
from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["RunToolTool"]


class RunToolTool:
    source = "kernel"
    broker = True
    prompt_visible = True
    name = "run_tool"
    description = "Run a tool by name with JSON object input"
    input_schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "input_json": {"type": "string"}},
        "required": ["name", "input_json"],
    }

    def __init__(self, tool_registry: object, usage_recorder: object | None = None) -> None:
        self._registry = tool_registry
        self._usage = usage_recorder
        self._parser = ToolInputJsonParser()

    def execute(self, parameters: dict) -> ToolResult:
        target = str(parameters.get("name", "")).strip()
        arguments = self._parser.parse(parameters.get("input_json"))
        failure = self._validation_error(target, arguments)
        return failure or self._executed(target, arguments)

    def _validation_error(self, target: str, arguments: object) -> ToolResult | None:
        if not target:
            return ToolResult(False, "run_tool requires a target tool name")
        if target not in {tool.name for tool in self._registry.all_tools()}:
            return ToolResult(False, f"unknown tool: {target}")
        if self._registry.is_broker(target):
            return ToolResult(False, f"cannot execute broker tool through run_tool: {target}")
        if not isinstance(arguments, dict):
            return ToolResult(False, "run_tool input_json must decode to an object")
        return self._invalid_argument_names(target, arguments) or self._missing_required_names(target, arguments)

    def _invalid_argument_names(self, target: str, arguments: dict) -> ToolResult | None:
        allowed = set(self._registry.get(target).input_schema.get("properties", {}).keys())
        invalid = sorted(set(arguments).difference(allowed))
        return ToolResult(False, f"invalid arguments for {target}: {', '.join(invalid)}") if invalid else None

    def _missing_required_names(self, target: str, arguments: dict) -> ToolResult | None:
        required = set(self._registry.get(target).input_schema.get("required", []))
        missing = sorted(name for name in required if name not in arguments)
        return ToolResult(False, f"missing arguments for {target}: {', '.join(missing)}") if missing else None

    def _executed(self, target: str, arguments: dict) -> ToolResult:
        try:
            result = self._registry.get(target).execute(arguments)
        except KeyError:
            return ToolResult(False, f"unknown tool: {target}")
        if self._usage:
            self._usage.record(target, result)
        return result
