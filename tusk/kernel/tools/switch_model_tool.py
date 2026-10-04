import re

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
        "Switch a slot's LLM. 'main agent' = slot main_agent (conversation_agent + command_agent). "
        f"model: {', '.join(_ALIASES)} or provider/model."
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
        slot = parameters["slot"]
        slots = _MAIN_AGENT_SLOTS if slot == _MAIN_AGENT else (slot,)
        try:
            models = [self._swap(underlying, parameters) for underlying in slots]
        except (KeyError, ValueError) as exc:
            # the registry only names in-use models; without the aliases the agent assumed nothing else exists
            return ToolResult(False, f"{exc}. Available: {', '.join(_ALIASES)}.")
        self._report_models()
        # without the directive the model kept re-issuing the same switch until max steps
        return ToolResult(True, _confirmation(slot, models[0]))

    def _swap(self, slot: str, parameters: dict) -> str:
        provider, model = self._resolve(slot, parameters)
        self._registry.swap(slot, provider, model)
        return model

    def _resolve(self, slot: str, parameters: dict) -> tuple[str, str]:
        provider, _, namespace = parameters.get("provider", "").partition("/")
        model = f"{namespace}/{parameters['model']}" if namespace else parameters["model"]
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
        return known or _ALIASES.get(model.casefold(), "") or _spoken_alias(model)

    def _report_models(self) -> None:
        if self._reporter is not None:
            self._reporter.set_models(self._registry.model_labels())


def _confirmation(slot: str, model: str) -> str:
    # naming only the requested slot: listing conversation_agent made the agent re-switch it unasked
    return f"{slot.replace('_', ' ').capitalize()} set to {model.rsplit('/', 1)[-1]}. Call done now to finish."


def _spoken_alias(model: str) -> str:
    # STT renders ids loosely ("GPT-OSS, $120 billion", "120B"); compare on bare lowercase alphanumerics
    spoken = _squash(model.casefold().replace("billion", "b"))
    matches = [full for alias, full in _ALIASES.items() if spoken and _squash(alias).endswith(spoken)]
    family = [alias for alias in _ALIASES if spoken and _squash(alias).startswith(spoken)]
    if not matches and len(family) > 1:
        raise ValueError(f"ambiguous model {model!r}: say {' or '.join(family)}")
    return matches[0] if len(matches) == 1 else ""


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text)
