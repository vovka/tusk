from abc import ABC

import pytest

from tusk.config import Config
from tusk.schemas.chat_message import ChatMessage
from tusk.schemas.desktop_context import DesktopContext, WindowInfo
from tusk.schemas.gate_result import GateResult
from tusk.schemas.llm_slot_config import LLMSlotConfig
from tusk.schemas.tool_call import ToolCall
from tusk.schemas.tool_result import ToolResult
from tusk.schemas.utterance import Utterance


def test_schema_dataclasses_and_helpers() -> None:
    msg = ChatMessage("user", "Previous context summary: x")
    assert msg.is_summary and msg.to_dict()["role"] == "user"
    assert ToolCall("x").parameters == {} and ToolResult(True, "ok").success
    assert Utterance("t", b"a", 0.1).confidence == 1.0
    assert GateResult(True, "go", 0.9).metadata == {}


def test_desktop_context_defaults() -> None:
    window = WindowInfo("1", "t", "a", False)
    ctx = DesktopContext("t", "a", [window])
    assert ctx.open_windows[0].window_id == "1"
    assert ctx.available_applications == []


def test_llm_slot_parse() -> None:
    parsed = LLMSlotConfig.parse("groq/model")
    assert parsed.provider_name == "groq"
    assert parsed.model == "model"


def test_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("AGENT_LLM", "openrouter/m")
    config = Config.from_env()
    assert config.groq_api_key == "k"
    assert config.agent_llm.provider_name == "openrouter"


def test_interfaces_are_abstract() -> None:
    import tusk.interfaces as interfaces

    classes = [v for v in vars(interfaces).values() if isinstance(v, type)]
    assert all(issubclass(cls, ABC) for cls in classes)
