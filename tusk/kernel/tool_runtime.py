from tusk.kernel.describe_tool_tool import DescribeToolTool
from tusk.kernel.find_tools_tool import FindToolsTool
from tusk.kernel.internal_tools import DictationRouter, StartDictationTool, SwitchModelTool
from tusk.kernel.run_tool_tool import RunToolTool
from tusk.kernel.tool_usage_recorder import ToolUsageRecorder
from tusk.kernel.tool_usage_store import ToolUsageStore

__all__ = ["ToolRuntime"]


class ToolRuntime:
    def __init__(
        self,
        config: object,
        tool_registry: object,
        llm_registry: object,
        adapter_manager: object,
        log: object,
    ) -> None:
        self._config = config
        self._registry = tool_registry
        self._llms = llm_registry
        self._manager = adapter_manager
        self._usage_store = ToolUsageStore(config.tool_usage_file, log=log)
        self._usage = ToolUsageRecorder(tool_registry, self._usage_store)

    @property
    def usage_recorder(self) -> ToolUsageRecorder:
        return self._usage

    def register_tools(self, pipeline: object) -> None:
        pipeline._dictation_router = DictationRouter(self._registry, pipeline)
        self._register_real_tools(pipeline)
        self._register_broker_tools()

    def _register_real_tools(self, pipeline: object) -> None:
        self._registry.register(SwitchModelTool(self._llms))
        self._registry.register(StartDictationTool(self._registry, pipeline, self._manager))

    def _register_broker_tools(self) -> None:
        self._registry.register(FindToolsTool(self._registry))
        self._registry.register(DescribeToolTool(self._registry))
        self._registry.register(RunToolTool(self._registry, self._usage))
