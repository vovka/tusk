import pytest

from tusk.shared.llm.llm_json import extract_json_payload


def test_parses_plain_json_object() -> None:
    assert extract_json_payload('{"stop": true}') == {"stop": True}


def test_parses_fenced_json() -> None:
    assert extract_json_payload('```json\n{"stop": true}\n```') == {"stop": True}


def test_scans_past_leading_prose_and_non_json_braces() -> None:
    assert extract_json_payload('Consider {x} then {"action": "none"} done') == {"action": "none"}


def test_unwraps_single_item_list() -> None:
    assert extract_json_payload('[{"action": "recover"}]') == {"action": "recover"}


def test_unwraps_tool_call_arguments() -> None:
    assert extract_json_payload('{"name": "gate", "arguments": {"stop": false}}') == {"stop": False}


def test_rejects_response_without_json_object() -> None:
    with pytest.raises(ValueError):
        extract_json_payload("no json here")


def test_rejects_non_object_json() -> None:
    with pytest.raises(ValueError):
        extract_json_payload("[1, 2]")
