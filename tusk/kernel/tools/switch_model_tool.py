from tusk.shared.schemas.tools.tool_result import ToolResult
from tusk.shared.llm.llm_registry import LLMRegistry
from tusk.shared.status.interfaces.status_reporter import StatusReporter

__all__ = ["SwitchModelTool"]

_MAIN_AGENT = "main_agent"
_MAIN_AGENT_SLOTS = ("conversation_agent", "command_agent")
_ALIASES = {
    "gpt-oss-120b": "groq/openai/gpt-oss-120b",
    "gpt-oss-20b": "groq/openai/gpt-oss-20b",
    "qwen3.8-27b": "groq/qwen/qwen3.8-27b",
}


class SwitchModelTool:
    source = "kernel"
    name = "switch_model"
    description = (
        "Switch a slot's LLM. 'main agent' is slot main_agent (both conversation_agent and command_agent). "
        "model: provider/model or a short id like gpt-oss-120b."
    )

    def __init__(self, llm_registry: LLMRegistry, reporter: StatusReporter | None = None) -> None:
        self._registry = llm_registry
        self._reporter = reporter

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "slot": {"type": "string", "enum": [*self._registry.slot_names, _MAIN_AGENT]},
                "provider": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": ["slot", "model"],
        }

    def execute(self, parameters: dict) -> ToolResult:
        slots = _MAIN_AGENT_SLOTS if parameters["slot"] == _MAIN_AGENT else (parameters["slot"],)
        try:
            messages = [self._swap(slot, parameters) for slot in slots]
        except (KeyError, ValueError) as exc:
            return ToolResult(False, str(exc))
        self._report_models()
        # without the directive the model kept re-issuing the same switch until max steps
        return ToolResult(True, f"{'; '.join(messages)}. Call done now to finish.")

    def _swap(self, slot: str, parameters: dict) -> str:
        provider, model = self._resolve(slot, parameters)
        return self._registry.swap(slot, provider, model)

    def _resolve(self, slot: str, parameters: dict) -> tuple[str, str]:
        provider, model = parameters.get("provider", ""), parameters["model"]
        labels = dict(self._registry.model_labels())
        providers = {label.split("/")[0] for label in labels.values()} | {provider}
        known = self._known_label(list(labels.values()), providers, f"{provider}/{model}" if provider else model)
        prefix, _, rest = (known or model).partition("/")
        if known or (rest and prefix in providers):
            return prefix, rest
        return provider or labels[slot].split("/")[0], model

    def _known_label(self, labels: list[str], providers: set[str], model: str) -> str:
        # a spoken short id ("gpt-oss-120b") maps to the full id a slot already uses ("groq/openai/gpt-oss-120b")
        prefix, _, rest = model.partition("/")
        wanted_provider = prefix if rest and prefix in providers else None
        short_id = model.rsplit("/", 1)[-1]
        matches = [label for label in labels if label.rsplit("/", 1)[-1] == short_id]
        known = next((label for label in matches if wanted_provider in (None, label.split("/")[0])), "")
        return known or _ALIASES.get(model.casefold(), "")

    def _report_models(self) -> None:
        if self._reporter is not None:
            self._reporter.set_models(self._registry.model_labels())
