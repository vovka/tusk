import types

from adapters.coding.coding_edit_planner import CodingEditPlanner


def test_plan_returns_new_buffer_from_structured_output() -> None:
    planner = CodingEditPlanner(_llm('{"buffer":"x\\na\\nb"}'))
    assert planner.plan("add x at the top", "a\nb") == "x\na\nb"


def test_plan_numbers_lines_and_passes_intent_to_llm() -> None:
    seen: list[str] = []
    planner = CodingEditPlanner(_capturing_llm(seen))
    planner.plan("rename foo", "def foo(): pass")
    assert "1| def foo(): pass" in seen[0]
    assert "rename foo" in seen[0]


def test_plan_returns_none_on_unparseable_output() -> None:
    planner = CodingEditPlanner(_llm("not json"))
    assert planner.plan("do something", "buffer") is None


def test_plan_returns_none_when_buffer_field_is_missing() -> None:
    planner = CodingEditPlanner(_llm("{}"))
    assert planner.plan("do something", "buffer") is None


def test_plan_strips_leaked_line_number_prefixes_from_response() -> None:
    planner = CodingEditPlanner(_llm('{"buffer":"1| function f() {\\n2|   return 1;\\n3| }"}'))
    assert planner.plan("do something", "function f() {\n  return 1;\n}") == "function f() {\n  return 1;\n}"


def test_schema_sets_additional_properties_false_for_groq_strict_mode() -> None:
    seen: list[dict] = []
    planner = CodingEditPlanner(_schema_capturing_llm(seen))
    planner.plan("do something", "buffer")
    assert seen[0]["additionalProperties"] is False


def _llm(response: str) -> object:
    return types.SimpleNamespace(complete_structured=lambda *args: response)


def _capturing_llm(seen: list[str]) -> object:
    return types.SimpleNamespace(complete_structured=lambda prompt, message, *rest: seen.append(message) or "{}")


def _schema_capturing_llm(seen: list[dict]) -> object:
    def complete_structured(prompt: str, message: str, schema_name: str, schema: dict, max_tokens: int) -> str:
        return seen.append(schema) or "{}"

    return types.SimpleNamespace(complete_structured=complete_structured)
