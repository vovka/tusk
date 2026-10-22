import json
import types
from pathlib import Path

from adapters.coding.server import TOOL_SCHEMAS as CODING_SCHEMAS
from adapters.dictation.server import TOOL_SCHEMAS as DICTATION_SCHEMAS
from adapters.gnome.tools.tool_schema_catalog import ToolSchemaCatalog
from tests.kernel_api_support import make_agent, make_registry_tool
from tusk.kernel.tools.switch_model_tool import SwitchModelTool
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult

# Groq's free tier caps a model at ~8K input tokens per minute; one command step must stay far below it.
_TOKEN_BUDGET_PER_CALL = 900
_SLOTS = ["gatekeeper", "stop_gate", "conversation_agent", "command_agent", "planner_agent", "executor_agent", "utility"]

_OPEN_EDITOR_AND_TYPE = [
    ToolCall("call_tool", {"name": "launch_application", "arguments": {"application_name": "text editor"}}),
    ToolCall("call_tool", {"name": "type_text", "arguments": {"text": "hello world"}}),
    ToolCall("done", {"status": "done", "summary": "Opened the text editor and typed hello world."}),
]


class _ScriptedLLM:
    label = "scripted"

    def __init__(self, calls: list[ToolCall]) -> None:
        self._calls = list(calls)
        self.token_estimates: list[int] = []

    def complete_tool_call(self, system_prompt: str, messages: list[dict], tools: list[dict]) -> ToolCall:
        self.token_estimates.append((len(system_prompt) + len(json.dumps(messages)) + len(json.dumps(tools))) // 4)
        return self._calls.pop(0)


def test_open_editor_and_type_takes_three_calls_under_token_budget() -> None:
    llm = _ScriptedLLM(_OPEN_EDITOR_AND_TYPE)
    executed: list[str] = []
    reply = make_agent(llm, registry=_desktop_registry(executed)).process_command("open the text editor and type hello world", "command")
    assert reply == "Opened the text editor and typed hello world."
    assert executed == ["gnome.launch_application", "gnome.type_text"]
    assert len(llm.token_estimates) == 3
    assert max(llm.token_estimates) <= _TOKEN_BUDGET_PER_CALL, llm.token_estimates


def _desktop_registry(executed: list[str]) -> ToolRegistry:
    registry = ToolRegistry()
    for source, schemas in (("gnome", ToolSchemaCatalog().build()), ("coding", CODING_SCHEMAS), ("dictation", DICTATION_SCHEMAS)):
        _register_adapter(registry, source, schemas, executed)
    registry.register(SwitchModelTool(types.SimpleNamespace(slot_names=_SLOTS)))
    for name in ("start_coding", "start_dictation"):
        registry.register(make_registry_tool(name, f"Start {name.split('_')[1]} mode", input_schema={"type": "object", "properties": {}}))
    return registry


def _register_adapter(registry: ToolRegistry, source: str, schemas: object, executed: list[str]) -> None:
    flags = json.loads((Path("adapters") / source / "adapter.json").read_text()).get("tools", {})
    for schema in schemas.values() if isinstance(schemas, dict) else schemas:
        flag = flags.get(schema["name"], {})
        name = f"{source}.{schema['name']}"
        execute = lambda parameters, name=name: executed.append(name) or ToolResult(True, "ok")
        tool = make_registry_tool(name, "ok", planner_visible=flag.get("planner_visible", True),
                                  sequence_callable=flag.get("sequence_callable", False), input_schema=schema["inputSchema"], execute=execute)
        registry.register(types.SimpleNamespace(**{**vars(tool), "description": schema["description"]}))
