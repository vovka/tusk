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


def test_executor_profile_has_no_run_agent() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert "run_agent" not in profiles["executor"].static_tool_names


def test_executor_profile_allows_runtime_tools() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert "*" in profiles["executor"].runtime_allowed_tool_names


def test_conversation_profile_max_steps() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert profiles["conversation"].max_steps == 8


def test_executor_profile_max_steps() -> None:
    profiles = build_agent_profiles(_mock_registry())
    assert profiles["executor"].max_steps == 16


def test_conversation_prompt_requires_completion_check_after_child() -> None:
    profiles = build_agent_profiles(_mock_registry())
    prompt = profiles["conversation"].system_prompt
    assert "already satisfied" in prompt
    assert "call done immediately" in prompt
    assert "fail twice" in prompt or "fails twice" in prompt


def test_executor_prompt_prefers_clipboard_for_large_text() -> None:
    profiles = build_agent_profiles(_mock_registry())
    prompt = profiles["executor"].system_prompt
    assert "clipboard" in prompt
    assert "gnome.write_clipboard" in prompt
    assert "intermediate actions before pasting" in prompt.lower()
    assert "do not copy or write to the clipboard again until after a paste" in prompt.lower()
    assert "not for literal text or urls" in prompt.lower()
    assert "tool named `done`" in prompt
    assert "single tool/function call" in prompt
    assert "do not write plain text" in prompt.lower()
