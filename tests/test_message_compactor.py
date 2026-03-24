from types import SimpleNamespace

from tusk.core.agent_message_compactor import AgentMessageCompactor
from tusk.core.recent_context_formatter import RecentContextFormatter
from tusk.schemas.chat_message import ChatMessage


def _compact(role: str, content: str) -> str:
    return AgentMessageCompactor().compact(ChatMessage(role, content)).content


def test_press_keys_compacted() -> None:
    raw = '{"tool":"press_keys","reply":"Pressing ctrl+a","keys":"ctrl+a"}'
    assert _compact("assistant", raw) == "[press_keys] Pressing ctrl+a"


def test_done_compacted() -> None:
    raw = '{"tool":"done","reply":"Done, Firefox is open."}'
    assert _compact("assistant", raw) == "[done] Done, Firefox is open."


def test_user_message_unchanged() -> None:
    assert _compact("user", "open Firefox and gedit") == "open Firefox and gedit"


def test_malformed_assistant_truncated() -> None:
    long_text = "not json at all and it is very long " * 10
    result = _compact("assistant", long_text)
    assert len(result) <= 100


def test_short_tool_result_unchanged() -> None:
    content = "Tool result: launched: firefox"
    assert _compact("user", content) == content


def test_long_tool_result_truncated() -> None:
    body = "a" * 200
    content = f"Tool result: {body}"
    result = _compact("user", content)
    assert len(result) <= 80
    assert result.startswith("Tool result:")
    assert "..." in result


def test_context_formatter_user_only() -> None:
    msgs = [ChatMessage("user", "open Firefox"), ChatMessage("assistant", "ok"), ChatMessage("user", "close it")]
    hist = SimpleNamespace(get_messages=lambda: msgs)
    text = RecentContextFormatter(hist).format_recent_context()
    assert "open Firefox" in text
    assert "close it" in text
    assert "ok" not in text
