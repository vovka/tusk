from tusk.kernel.sliding_window_history import SlidingWindowHistory
from tusk.shared.schemas.chat_message import ChatMessage


def test_appends_and_returns_copies() -> None:
    history = SlidingWindowHistory(4)
    history.append(ChatMessage("user", "hello"))
    messages = history.get_messages()
    messages.clear()
    assert [m.content for m in history.get_messages()] == ["hello"]


def test_compacts_past_max_with_local_summary() -> None:
    history = SlidingWindowHistory(4)
    for index in range(5):
        history.append(ChatMessage("user", f"message {index}"))
    messages = history.get_messages()
    assert len(messages) == 4
    assert messages[0].content.startswith("Previous context summary: ")
    assert "message 1" in messages[0].content


def test_clear_empties_history() -> None:
    history = SlidingWindowHistory(4)
    history.append(ChatMessage("user", "hello"))
    history.clear()
    assert history.get_messages() == []
