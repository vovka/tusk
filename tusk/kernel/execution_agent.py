from tusk.kernel.agent_tool_loop import AgentToolLoop
from tusk.kernel.execution_tool_definition_list import ExecutionToolDefinitionList
from tusk.kernel.interfaces.task_executor import TaskExecutor
from tusk.kernel.schemas.task_execution_result import TaskExecutionResult
from tusk.kernel.schemas.task_plan import TaskPlan
from tusk.kernel.tool_registry import ToolRegistry

__all__ = ["ExecutionAgent"]

_PROMPT = "\n".join([
    "You execute TUSK task plans.",
    "Use exactly one tool per response.",
    "Use only the tools provided in this execution session.",
    "Split long literal text into multiple gnome.type_text calls.",
    "Keep each gnome.type_text text argument short, about 300 characters or less.",
    "Use done when the task is complete.",
    "Use clarify when the user must answer one short question.",
    "Use unknown when the task cannot be handled.",
    "Use need_tools when the provided tool subset is insufficient.",
])


class ExecutionAgent(TaskExecutor):
    def __init__(self, llm_provider: object, tool_registry: ToolRegistry, log_printer: object) -> None:
        self._loop = AgentToolLoop(llm_provider, tool_registry, log_printer)
        self._registry = tool_registry
        self._tools = ExecutionToolDefinitionList()

    def execute(self, task: str, plan: TaskPlan) -> TaskExecutionResult:
        selected = set(plan.selected_tools)
        history = [{"role": "user", "content": self._message(task, plan)}]
        return self._loop.run(_PROMPT, history, self._tools.build(self._registry.definitions_for(selected)), selected, self._terminal_names())

    def _message(self, task: str, plan: TaskPlan) -> str:
        steps = "\n".join(f"- {step}" for step in plan.plan_steps)
        return f"Task:\n{task}\n\nPlan:\n{steps}"

    def _terminal_names(self) -> set[str]:
        return {"done", "clarify", "unknown", "need_tools"}
