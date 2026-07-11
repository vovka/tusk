import types

import main
from tusk.shared.interrupt import InterruptToken
from tusk.shared.llm import LLMRegistry
from tusk.shared.tracing.null_tracer import NullTracer


def _slot_config() -> types.SimpleNamespace:
    return types.SimpleNamespace(provider_name="groq", model="some-model")


def _config() -> types.SimpleNamespace:
    names = (
        "gatekeeper_llm", "stop_gate_llm", "conversation_agent_llm",
        "planner_agent_llm", "executor_agent_llm", "default_agent_llm", "utility_llm",
    )
    return types.SimpleNamespace(**{name: _slot_config() for name in names})


def test_register_slots_includes_stop_gate() -> None:
    registry = LLMRegistry(types.SimpleNamespace())
    factory = types.SimpleNamespace(create=lambda provider, model: types.SimpleNamespace(label=f"{provider}/{model}"))
    log = types.SimpleNamespace(log=lambda *args: None, show_wait=lambda *args: None, clear_wait=lambda: None)
    options = types.SimpleNamespace(log_groups=frozenset(), llm_log_preview_chars=120)
    main._register_slots(factory, _config(), log, registry, options, InterruptToken(), NullTracer())
    assert "stop_gate" in registry.slot_names
    assert "gatekeeper" in registry.slot_names
