import types

from tusk.kernel.agent_profiles import build_agent_profiles


def test_sequence_prompt_contracts_are_present() -> None:
    profiles = build_agent_profiles(_registry())
    assert "execution_mode" in profiles["planner"].system_prompt
    assert "provided tool catalog" in profiles["planner"].system_prompt
    assert "planned_steps" in profiles["planner"].system_prompt
    assert "promote the plan to sequence" in profiles["planner"].system_prompt
    assert "execute_tool_sequence" in profiles["executor"].system_prompt
    assert "empty arguments" in profiles["executor"].system_prompt
    assert "Do not rewrite or reconstruct" in profiles["executor"].system_prompt


def _registry() -> object:
    llm = object()
    items = {name: llm for name in ["conversation_agent", "planner_agent", "executor_agent", "default_agent"]}
    return types.SimpleNamespace(get=lambda name: items[name])
