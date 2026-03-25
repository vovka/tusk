from tusk.kernel.schemas.tool_result import ToolResult

__all__ = ["ExecuteTaskTool"]


class ExecuteTaskTool:
    name = "execute_task"
    description = "Plan and execute a user task, then return the final result."
    planner_visible = False
    source = "kernel"
    input_schema = {
        "type": "object",
        "properties": {"task": {"type": "string"}},
        "required": ["task"],
        "additionalProperties": False,
    }

    def __init__(self, service: object) -> None:
        self._service = service

    def execute(self, parameters: dict[str, object]) -> ToolResult:
        task = str(parameters.get("task", "")).strip()
        if not task:
            return ToolResult(False, "execute_task requires a task")
        result = self._service.run(task)
        return ToolResult(result.status != "failed", result.reply, {"status": result.status, "reason": result.reason})
