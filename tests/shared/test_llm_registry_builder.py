import types

from tusk.shared.interrupt_token import InterruptToken
from tusk.shared.llm import LLMRegistryBuilder, RotatingLLMProvider
from tusk.shared.observability.null_tracer import NullTracer
from tusk.shared.schemas.llm_slot_config import LLMSlotConfig

_SLOT_NAMES = ("gatekeeper", "stop_gate", "conversation_agent", "command_agent", "planner_agent", "executor_agent", "default_agent", "utility")


class _Factory:
    def create(self, provider_name: str, model: str) -> types.SimpleNamespace:
        return types.SimpleNamespace(label=f"{provider_name}/{model}")


def _config(command_agent: str = "groq/m1") -> types.SimpleNamespace:
    slots = {f"{name}_llm": LLMSlotConfig.parse("groq/some-model") for name in _SLOT_NAMES}
    slots["command_agent_llm"] = LLMSlotConfig.parse(command_agent)
    return types.SimpleNamespace(**slots)


def _builder(config: types.SimpleNamespace, token: InterruptToken) -> LLMRegistryBuilder:
    log = types.SimpleNamespace(log=lambda *args: None, show_wait=lambda *args: None, clear_wait=lambda: None)
    options = types.SimpleNamespace(log_groups=frozenset(), llm_log_preview_chars=120)
    return LLMRegistryBuilder(_Factory(), config, log, options, token, NullTracer())


def test_build_registers_every_slot() -> None:
    registry = _builder(_config(), InterruptToken()).build()
    assert tuple(registry.slot_names) == _SLOT_NAMES


def test_rotation_slot_gets_rotating_provider_and_can_be_swapped() -> None:
    registry = _builder(_config("groq/m1,groq/m2"), InterruptToken()).build()
    assert isinstance(registry.get("command_agent")._inner, RotatingLLMProvider)
    assert registry.get("command_agent").label == "groq/m1"
    registry.swap("command_agent", "groq", "m3")
    assert dict(registry.model_labels())["command_agent"] == "groq/m3"


def test_gate_and_utility_slots_ignore_interrupt_token() -> None:
    token = InterruptToken()
    registry = _builder(_config(), token).build()
    assert registry.get("gatekeeper")._retry._token is None
    assert registry.get("stop_gate")._retry._token is None
    assert registry.get("utility")._retry._token is None
    assert registry.get("command_agent")._retry._token is token
