from tusk.core.agent import MainAgent
from tusk.core.color_log_printer import ColorLogPrinter
from tusk.core.llm_conversation_summarizer import LLMConversationSummarizer
from tusk.core.llm_proxy import LLMProxy
from tusk.core.llm_registry import LLMRegistry
from tusk.core.recent_context_formatter import RecentContextFormatter
from tusk.core.sliding_window_history import SlidingWindowHistory
from tusk.core.tool_registry import ToolRegistry
from tusk.schemas.chat_message import ChatMessage
from tusk.schemas.desktop_context import DesktopContext
from tusk.schemas.tool_result import ToolResult


def test_tool_registry_schema() -> None:
    tool = type("T", (), {"name": "x", "parameters_schema": {"a": "b"}})()
    reg = ToolRegistry()
    reg.register(tool)
    assert '"tool": "x"' in reg.build_schema_text()


def test_llm_registry_swap_and_proxy() -> None:
    p1 = type("P", (), {"label": "a", "complete": lambda *a: "x", "complete_messages": lambda *a: "x"})()
    p2 = type("P", (), {"label": "b", "complete": lambda *a: "y", "complete_messages": lambda *a: "y"})()
    factory = type("F", (), {"create": lambda *a: p2})()
    reg = LLMRegistry(factory)
    reg.register_slot("agent", LLMProxy(p1))
    assert reg.swap("agent", "groq", "m") == "agent -> groq/m"


def test_history_formatter_and_summarizer() -> None:
    llm = type("L", (), {"complete": lambda *a: "sum"})()
    hist = SlidingWindowHistory(2, LLMConversationSummarizer(llm))
    hist.append(ChatMessage("user", "a")); hist.append(ChatMessage("assistant", "b")); hist.append(ChatMessage("user", "c"))
    text = RecentContextFormatter(hist).format_recent_context()
    assert "Previous context summary:" in hist.get_messages()[0].content and "User" in text


def test_main_agent_tool_loop_and_unknown() -> None:
    llm = type("L", (), {"label": "x", "complete_messages": lambda *a: '{"tool":"unknown","reason":"no"}'})()
    ctx = type("C", (), {"get_context": lambda *a: DesktopContext("t", "a")})()
    hist = SlidingWindowHistory(20, type("S", (), {"summarize": lambda *a: "s"})())
    tool = type("T", (), {"name": "noop", "parameters_schema": {}, "execute": lambda *a: ToolResult(True, "ok")})()
    reg = ToolRegistry(); reg.register(tool)
    MainAgent(llm, ctx, reg, hist, type("P", (), {"log": lambda *a: None})()).process_command("do")
    assert len(hist.get_messages()) >= 2


def test_color_log_printer(capsys) -> None:
    ColorLogPrinter().log("STT", "ok")
    assert "[STT] ok" in capsys.readouterr().out
