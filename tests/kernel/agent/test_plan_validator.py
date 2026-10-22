from tests.kernel_api_support import make_registry_tool
from tusk.kernel.agent.tool_sequence.plan_validator import PlanValidator
from tusk.kernel.tools.tool_registry import ToolRegistry
from tusk.shared.schemas.tools.tool_sequence_plan import ToolSequencePlan


def test_validate_steps_accepts_valid_plan() -> None:
    assert _validator().validate_steps(_plan([_step("s1")])) is None


def test_validate_steps_requires_at_least_one_step() -> None:
    assert _validator().validate_steps(_plan([])) == "planned_steps requires at least one step"


def test_validate_steps_rejects_more_than_eight_steps() -> None:
    plan = _plan([_step(f"s{index}") for index in range(9)])
    assert _validator().validate_steps(plan) == "planned_steps exceeds max steps (8)"


def test_validate_steps_rejects_duplicate_ids() -> None:
    plan = _plan([_step("s1"), _step("s1")])
    assert _validator().validate_steps(plan) == "planned_steps contains duplicate step ids"


def test_validate_steps_rejects_synthetic_tools() -> None:
    plan = _plan([_step("s1", "done")])
    assert _validator().validate_steps(plan) == "s1: synthetic tools are not allowed in planned_steps"


def test_validate_steps_rejects_unknown_tool() -> None:
    assert _validator().validate_steps(_plan([_step("s1", "gnome.missing")])) == "s1: unknown tool: gnome.missing"


def test_validate_steps_rejects_bad_args() -> None:
    plan = _plan([_step("s1", args={"text": 5})])
    message = _validator().validate_steps(plan)
    assert message is not None and message.startswith("s1: ")


def test_validate_steps_ignores_sequence_callable() -> None:
    assert _validator(sequence_callable=False).validate_steps(_plan([_step("s1")])) is None


def test_validate_sequence_rejects_non_sequence_callable_tool() -> None:
    message = _validator(sequence_callable=False).validate_sequence(_plan([_step("s1")]), {"gnome.type_text"})
    assert message == "s1: tool is not sequence_callable: gnome.type_text"


def test_validate_sequence_rejects_tool_set_mismatch() -> None:
    message = _validator().validate_sequence(_plan([_step("s1")]), {"gnome.type_text", "gnome.other"})
    assert message == "sequence_plan tool set must match selected_tool_names"


def test_validate_sequence_runs_step_checks_first() -> None:
    plan = _plan([_step("s1"), _step("s1")])
    assert _validator().validate_sequence(plan, {"gnome.type_text"}) == "sequence_plan contains duplicate step ids"


def test_validate_sequence_labels_step_errors_as_sequence_plan() -> None:
    assert _validator().validate_sequence(_plan([]), set()) == "sequence_plan requires at least one step"


def test_validate_sequence_labels_synthetic_tool_errors_as_sequence_plan() -> None:
    message = _validator().validate_sequence(_plan([_step("s1", "done")]), {"done"})
    assert message == "s1: synthetic tools are not allowed in sequence_plan"


def test_validate_sequence_checks_sequence_callable_before_args() -> None:
    plan = _plan([_step("s1", args={"text": 5})])
    message = _validator(sequence_callable=False).validate_sequence(plan, {"gnome.type_text"})
    assert message == "s1: tool is not sequence_callable: gnome.type_text"


def test_validate_sequence_accepts_valid_plan() -> None:
    assert _validator().validate_sequence(_plan([_step("s1")]), {"gnome.type_text"}) is None


def _validator(sequence_callable: bool = True) -> PlanValidator:
    registry = ToolRegistry()
    registry.register(make_registry_tool("gnome.type_text", "type", sequence_callable=sequence_callable))
    return PlanValidator(registry)


def _plan(steps: list[dict[str, object]]) -> ToolSequencePlan:
    plan = ToolSequencePlan.from_dict({"goal": "Type hello", "steps": steps})
    assert plan is not None
    return plan


def _step(step_id: str, tool_name: str = "gnome.type_text", args: dict[str, object] | None = None) -> dict[str, object]:
    return {"id": step_id, "tool_name": tool_name, "args": args if args is not None else {"text": "hello"}}
