from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.shared.llm.llm_registry import LLMRegistry
from tusk.shared.status.interfaces.status_reporter import StatusReporter

__all__ = ["SwitchModelTool"]


class SwitchModelTool:
    source = "kernel"
    name = "switch_model"
    description = (
        "Switch the LLM model of a slot. 'main agent' means the conversation_agent and command_agent slots "
        "(call once per slot). model is 'provider/model' (e.g. groq/openai/gpt-oss-120b) or a bare model id, "
        "which keeps the slot's current provider. provider is optional."
    )

    def __init__(self, llm_registry: LLMRegistry, reporter: StatusReporter | None = None) -> None:
        self._registry = llm_registry
        self._reporter = reporter

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "slot": {"type": "string", "enum": self._registry.slot_names},
                "provider": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": ["slot", "model"],
        }

    def execute(self, parameters: dict) -> ToolResult:
        try:
            provider, model = self._resolve(parameters)
            message = self._registry.swap(parameters["slot"], provider, model)
        except (KeyError, ValueError) as exc:
            return ToolResult(False, str(exc))
        self._report_models()
        return ToolResult(True, message)

    def _resolve(self, parameters: dict) -> tuple[str, str]:
        if parameters.get("provider"):
            return parameters["provider"], parameters["model"]
        labels = dict(self._registry.model_labels())
        current_provider = labels[parameters["slot"]].split("/")[0]
        known_providers = {label.split("/")[0] for label in labels.values()}
        prefix, _, rest = parameters["model"].partition("/")
        if rest and prefix in known_providers:
            return prefix, rest
        return current_provider, parameters["model"]

    def _report_models(self) -> None:
        if self._reporter is not None:
            self._reporter.set_models(self._registry.model_labels())
