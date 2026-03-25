from tusk.kernel.execute_task_tool import ExecuteTaskTool
from tusk.kernel.execution_agent import ExecutionAgent
from tusk.kernel.fallback_task_planner import FallbackTaskPlanner
from tusk.kernel.internal_tools import DictationRouter, StartDictationTool, SwitchModelTool
from tusk.kernel.llm_task_planner import LLMTaskPlanner
from tusk.kernel.task_execution_service import TaskExecutionService

__all__ = ["ToolRuntime"]


class ToolRuntime:
    def __init__(self, tool_registry: object, llm_registry: object, adapter_manager: object, log: object) -> None:
        self._registry = tool_registry
        self._llms = llm_registry
        self._manager = adapter_manager
        self._log = log

    def register_tools(self, pipeline: object) -> None:
        pipeline._dictation_router = DictationRouter(self._registry, pipeline)
        self._registry.register(SwitchModelTool(self._llms))
        self._registry.register(StartDictationTool(self._registry, pipeline, self._manager))
        self._registry.register(ExecuteTaskTool(self._service()))

    def _service(self) -> TaskExecutionService:
        planner = self._planner()
        executor = ExecutionAgent(self._llms.get("agent"), self._registry, self._log)
        return TaskExecutionService(planner, executor, self._registry, self._log)

    def _planner(self) -> object:
        primary = LLMTaskPlanner(self._llms.get("planner"), self._log)
        secondary = LLMTaskPlanner(self._llms.get("utility"), self._log)
        return FallbackTaskPlanner(primary, secondary, self._log)
