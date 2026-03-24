from tusk.core.agent import MainAgent
from tusk.core.sliding_window_history import SlidingWindowHistory
from tusk.core.tool_registry import ToolRegistry
from tusk.schemas.desktop_context import DesktopContext
from tusk.schemas.tool_result import ToolResult


def _make_agent(llm_response: str) -> tuple:
    llm = type("L", (), {"label": "x", "complete_messages": lambda *a: llm_response})()
    ctx = type("C", (), {"get_context": lambda *a: DesktopContext("t", "a")})()
    hist = SlidingWindowHistory(20, type("S", (), {"summarize": lambda *a: "s"})())
    reg = ToolRegistry()
    log = type("P", (), {"log": lambda *a: None})()
    agent = MainAgent(llm, ctx, reg, hist, log)
    return agent, hist, log


def test_clarify_stops_loop() -> None:
    agent, hist, _ = _make_agent('{"tool":"clarify","reply":"What do you mean?"}')
    agent.process_command("do the thing")
    messages = hist.get_messages()
    assert len(messages) == 2


def test_clarify_reply_is_logged() -> None:
    logged = []
    agent, _, log = _make_agent('{"tool":"clarify","reply":"Could you be more specific?"}')
    log.log = lambda tag, msg: logged.append((tag, msg))
    agent.process_command("do the thing")
    assert any("Could you be more specific?" in msg for _, msg in logged)


def test_done_still_works() -> None:
    agent, hist, _ = _make_agent('{"tool":"done","reply":"Done!"}')
    agent.process_command("open Firefox")
    messages = hist.get_messages()
    assert len(messages) == 2
