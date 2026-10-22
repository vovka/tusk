from tusk.kernel.agent.guards.conversation_delegation_guard import ConversationDelegationGuard
from tusk.shared.schemas.tools.tool_call import ToolCall
from tusk.shared.schemas.tools.tool_result import ToolResult


def _run_agent() -> ToolCall:
    return ToolCall("run_agent", {"profile_id": "executor", "instruction": "x"}, "c1")


def _child(status: str) -> ToolResult:
    return ToolResult(True, "ok", {"child_result": {"profile_id": "executor", "status": status}})


def test_no_violation_before_any_child() -> None:
    assert ConversationDelegationGuard().violation("conversation", _run_agent()) is None


def test_blocks_delegation_after_child_done() -> None:
    guard = ConversationDelegationGuard()
    guard.observe(_run_agent(), _child("done"))
    assert "must call done after executor" in guard.violation("conversation", _run_agent())


def test_blocks_delegation_after_failure_budget_exhausted() -> None:
    guard = ConversationDelegationGuard()
    guard.observe(_run_agent(), _child("failed"))
    assert guard.violation("conversation", _run_agent()) is None
    guard.observe(_run_agent(), _child("need_tools"))
    assert "retry budget" in guard.violation("conversation", _run_agent())


def test_ignores_other_profiles_and_tools() -> None:
    guard = ConversationDelegationGuard()
    guard.observe(_run_agent(), _child("done"))
    assert guard.violation("executor", _run_agent()) is None
    assert guard.violation("conversation", ToolCall("done", {}, "c2")) is None
