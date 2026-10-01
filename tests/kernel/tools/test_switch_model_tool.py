import types

from tusk.kernel.core.agent_profiles import build_agent_profiles
from tusk.kernel.tools.switch_model_tool import SwitchModelTool

_LABELS = (("conversation_agent", "groq/openai/gpt-oss-20b"), ("command_agent", "openrouter/x/y"))


def _registry(swaps: list) -> object:
    return types.SimpleNamespace(
        slot_names=["conversation_agent", "command_agent"],
        model_labels=lambda: _LABELS,
        swap=lambda slot, provider, model: swaps.append((slot, provider, model)) or "ok",
    )


def _execute(parameters: dict) -> list:
    swaps: list = []
    SwitchModelTool(_registry(swaps)).execute(parameters)
    return swaps


def test_slot_enum_lists_registry_slot_names() -> None:
    schema = SwitchModelTool(_registry([])).input_schema
    assert schema["properties"]["slot"]["enum"] == ["conversation_agent", "command_agent"]


def test_description_maps_main_agent_to_slots() -> None:
    description = SwitchModelTool(_registry([])).description
    assert "main agent" in description and "conversation_agent" in description and "command_agent" in description


def test_provider_is_not_required() -> None:
    assert SwitchModelTool(_registry([])).input_schema["required"] == ["slot", "model"]


def test_model_with_known_provider_prefix_is_split() -> None:
    swaps = _execute({"slot": "command_agent", "model": "groq/openai/gpt-oss-120b"})
    assert swaps == [("command_agent", "groq", "openai/gpt-oss-120b")]


def test_bare_model_uses_current_provider_of_slot() -> None:
    swaps = _execute({"slot": "conversation_agent", "model": "openai/gpt-oss-120b"})
    assert swaps == [("conversation_agent", "groq", "openai/gpt-oss-120b")]


def test_explicit_provider_is_kept() -> None:
    swaps = _execute({"slot": "command_agent", "provider": "groq", "model": "m"})
    assert swaps == [("command_agent", "groq", "m")]


def test_command_prompt_mentions_model_switching() -> None:
    llms = types.SimpleNamespace(get=lambda name: types.SimpleNamespace(label=name))
    prompt = build_agent_profiles(llms)["command"].system_prompt
    assert "switch_model" in prompt
