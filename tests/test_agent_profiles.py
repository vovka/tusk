import types

from tusk.kernel.agent_profiles import build_agent_profiles


def _mock_registry() -> object:
    llms = {
        "conversation_agent": types.SimpleNamespace(label="conversation"),
        "planner_agent": types.SimpleNamespace(label="planner"),
        "executor_agent": types.SimpleNamespace(label="executor"),
        "default_agent": types.SimpleNamespace(label="default"),
    }
    return types.SimpleNamespace(get=lambda name: llms[name])


def test_build_returns_four_profiles() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert set(profiles.keys()) == {"conversation", "planner", "executor", "default"}


def test_conversation_profile_has_run_agent() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert "run_agent" in profiles["conversation"].static_tool_names


def test_planner_profile_has_list_tools() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert "list_available_tools" in profiles["planner"].static_tool_names


def test_executor_profile_allows_runtime_tools() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert "*" in profiles["executor"].runtime_allowed_tool_names


def test_conversation_profile_max_steps() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert profiles["conversation"].max_steps == 8


def test_executor_profile_max_steps() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert profiles["executor"].max_steps == 16
