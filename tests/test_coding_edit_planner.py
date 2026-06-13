import types

from adapters.coding.coding_edit_planner import CodingEditPlanner


def test_plan_returns_operations_from_structured_output() -> None:
    planner = CodingEditPlanner(_llm('{"operations":[{"kind":"insert","target_start":1,"target_end":1,"new_text":"x"}]}'))
    operations = planner.plan("add x at the top", "a\nb")
    assert operations == [{"kind": "insert", "target_start": 1, "target_end": 1, "new_text": "x"}]


def test_plan_passes_buffer_and_intent_to_llm() -> None:
    seen: list[str] = []
    planner = CodingEditPlanner(_capturing_llm(seen))
    planner.plan("rename foo", "def foo(): pass")
    assert "def foo(): pass" in seen[0]
    assert "rename foo" in seen[0]


def test_plan_returns_empty_on_unparseable_output() -> None:
    planner = CodingEditPlanner(_llm("not json"))
    assert planner.plan("do something", "buffer") == []


def _llm(response: str) -> object:
    return types.SimpleNamespace(complete_structured=lambda *args: response)


def _capturing_llm(seen: list[str]) -> object:
    return types.SimpleNamespace(complete_structured=lambda prompt, message, *rest: seen.append(message) or "{}")
