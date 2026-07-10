import types

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
