import types

from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.agent_profile import AgentProfile
from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.agent_toolset_builder import AgentToolsetBuilder
from tusk.kernel.tools.tool_registry import ToolRegistry


def _builder() -> AgentToolsetBuilder:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.press_keys", "pressed"))
    registry.register(make_registry_tool("gnome.type_text", "typed"))
    return AgentToolsetBuilder(registry)


def _builder_with_hidden() -> AgentToolsetBuilder:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.press_keys", "pressed"))
    registry.register(make_registry_tool("dictation.start_dictation", "started", planner_visible=False))
    return AgentToolsetBuilder(registry)


def test_command_wildcard_excludes_hidden_adapter_internals() -> None:
    request = AgentRunRequest("start dictation", "command", runtime_tool_names=("*",), gate_command=True)
    assert _builder_with_hidden().runtime_names(_profile(), request) == {"gnome.press_keys"}


def test_delegated_command_profile_does_not_expand_wildcard() -> None:
    request = AgentRunRequest("x", "command", runtime_tool_names=("*",), parent_call_id="call-1")
    assert _builder().runtime_names(_profile(), request) == set()


def test_recovered_command_without_gate_flag_does_not_expand_wildcard() -> None:
    # a recovered ToolCall has call_id="" -> the child's parent_call_id is "" too, but gate_command stays False
    request = AgentRunRequest("x", "command", runtime_tool_names=("*",), parent_call_id="")
    assert _builder().runtime_names(_profile(), request) == set()


def _profile() -> AgentProfile:
    return AgentProfile("command", types.SimpleNamespace(label="llm"), "prompt", ("run_agent",), ("*",), 8)


def _executor_profile() -> AgentProfile:
    return AgentProfile("executor", types.SimpleNamespace(label="llm"), "prompt", (), ("*",), 16)


def test_executor_wildcard_request_does_not_expand_to_all_tools() -> None:
    request = AgentRunRequest("x", "executor", runtime_tool_names=("*",))
    assert _builder().runtime_names(_executor_profile(), request) == set()


def test_executor_receives_only_explicitly_selected_real_tools() -> None:
    request = AgentRunRequest("x", "executor", runtime_tool_names=("gnome.press_keys", "*"))
    assert _builder().runtime_names(_executor_profile(), request) == {"gnome.press_keys"}


def test_wildcard_request_expands_to_all_real_tools() -> None:
    request = AgentRunRequest("open gedit", "command", runtime_tool_names=("*",), gate_command=True)
    assert _builder().runtime_names(_profile(), request) == {"gnome.press_keys", "gnome.type_text"}


def test_explicit_names_still_filter_against_real_tools() -> None:
    request = AgentRunRequest("x", "command", runtime_tool_names=("gnome.press_keys", "gnome.missing"))
    assert _builder().runtime_names(_profile(), request) == {"gnome.press_keys"}
