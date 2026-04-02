from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.agent_run_request import AgentRunRequest
from tusk.kernel.agent.agent_toolset_builder import AgentToolsetBuilder
from tusk.kernel.agent_profiles import build_agent_profiles
from tusk.kernel.tool_registry import ToolRegistry
from tusk.shared.schemas.tool_sequence_plan import ToolSequencePlan


def test_sequence_executor_gets_meta_tool_only() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=True))
    tools = AgentToolsetBuilder(registry).build(_profiles()["executor"], _sequence_request())
    names = [tool["function"]["name"] for tool in tools]
    assert names == ["done", "execute_tool_sequence"]
    assert tools[1]["function"]["parameters"] == {"type": "object", "properties": {}, "additionalProperties": False}


def test_normal_executor_keeps_runtime_tools() -> None:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=True))
    request = AgentRunRequest("type", profile_id="executor", runtime_tool_names=("gnome.type_text",))
    tools = AgentToolsetBuilder(registry).build(_profiles()["executor"], request)
    names = [tool["function"]["name"] for tool in tools]
    assert names == ["done", "gnome.type_text"]


def _profiles() -> dict[str, object]:
    llm = object()
    registry = {"conversation_agent": llm, "planner_agent": llm, "executor_agent": llm, "default_agent": llm}
    return build_agent_profiles(type("Registry", (), {"get": lambda self, name: registry[name]})())


def _plan() -> dict[str, object]:
    return {"goal": "Type hello", "steps": [{"id": "s1", "tool_name": "gnome.type_text", "args": {"text": "hello"}}]}


def _sequence_request() -> AgentRunRequest:
    plan = ToolSequencePlan.from_dict(_plan())
    return AgentRunRequest("type", "executor", runtime_tool_names=("gnome.type_text",), execution_mode="sequence", sequence_plan=plan)
