import types

import pytest

from tusk.kernel.tools.switch_model_tool import SwitchModelTool
from tusk.providers.llm import groq_llm
from tusk.providers.llm.configurable_llm_factory import ConfigurableLLMFactory
from tusk.shared.llm import LLMProxy, LLMRegistry

_SERVED = ("openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b")
_SLOTS = ("conversation_agent", "command_agent", "utility")


class _FakeGroq:
    def __init__(self, **kwargs: object) -> None:
        listing = types.SimpleNamespace(data=[types.SimpleNamespace(id=model) for model in _SERVED])
        self.models = types.SimpleNamespace(list=lambda: listing)


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> LLMRegistry:
    monkeypatch.setattr(groq_llm, "Groq", _FakeGroq)
    factory = ConfigurableLLMFactory("key", "")
    registry = LLMRegistry(factory)
    for slot in _SLOTS:
        registry.register_slot(slot, LLMProxy(factory.create("groq", "openai/gpt-oss-20b"), slot_name=slot))
    return registry


def _labels(registry: LLMRegistry) -> dict:
    return dict(registry.model_labels())


# Arguments the command agent actually produced for "set the main agent to GPT OSS 120B" in the 2 Oct Incus takes
# (video/src2/swap.log, fail3/swap.log, fail2/swap_e2e_*.log), replayed through the real registry, proxy and Groq provider.
@pytest.mark.parametrize("arguments", [
    {"model": "gpt-oss-120b", "slot": "main_agent"},
    {"model": "gpt-oss-120b", "provider": "groq/openai", "slot": "main_agent"},
    {"model": "openai/gpt-oss-120b", "provider": "groq", "slot": "main_agent"},
    {"model": "GPT-OSS, $120 billion", "slot": "main_agent"},
])
def test_observed_main_agent_calls_switch_both_agent_slots(registry: LLMRegistry, arguments: dict) -> None:
    result = SwitchModelTool(registry).execute(arguments)
    labels = _labels(registry)
    assert result.success and result.message.startswith("Main agent set to gpt-oss-120b.")
    assert labels["conversation_agent"] == labels["command_agent"] == "groq/openai/gpt-oss-120b"
    assert labels["utility"] == "groq/openai/gpt-oss-20b"


def test_repeating_the_same_switch_is_harmless(registry: LLMRegistry) -> None:
    tool = SwitchModelTool(registry)
    for _ in range(3):
        assert tool.execute({"model": "gpt-oss-120b", "slot": "main_agent"}).success
    assert _labels(registry)["command_agent"] == "groq/openai/gpt-oss-120b"


@pytest.mark.parametrize("model", ["banana", "gpt-oss"])
def test_unservable_or_ambiguous_model_changes_nothing_and_lists_options(registry: LLMRegistry, model: str) -> None:
    before = _labels(registry)
    result = SwitchModelTool(registry).execute({"model": model, "slot": "main_agent"})
    assert not result.success and "gpt-oss-120b" in result.message
    assert _labels(registry) == before
