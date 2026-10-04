import types

import pytest

from tusk.shared.llm.llm_registry import LLMRegistry


def _registry() -> LLMRegistry:
    return LLMRegistry(types.SimpleNamespace())


def test_get_with_fallback_prefers_the_named_slot() -> None:
    registry = _registry()
    gatekeeper, stop_gate = object(), object()
    registry.register_slot("gatekeeper", gatekeeper)
    registry.register_slot("stop_gate", stop_gate)
    assert registry.get_with_fallback("stop_gate", "gatekeeper") is stop_gate


def test_get_with_fallback_uses_fallback_when_slot_missing() -> None:
    registry = _registry()
    gatekeeper = object()
    registry.register_slot("gatekeeper", gatekeeper)
    assert registry.get_with_fallback("stop_gate", "gatekeeper") is gatekeeper


def test_swap_rejects_model_that_fails_verification() -> None:
    def verify() -> None:
        raise RuntimeError("404 model_not_found")
    factory = types.SimpleNamespace(create=lambda provider, model: types.SimpleNamespace(verify=verify))
    registry = LLMRegistry(factory)
    registry.register_slot("command_agent", types.SimpleNamespace(label="groq/openai/gpt-oss-20b", swap=None))
    with pytest.raises(ValueError, match="unknown model groq/bogus; known: groq/openai/gpt-oss-20b"):
        registry.swap("command_agent", "groq", "bogus")
    assert registry.model_labels() == (("command_agent", "groq/openai/gpt-oss-20b"),)
