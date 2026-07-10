from shells.voice.stages.gate.gatekeeper_parser import parse_gate_result, parse_recovery_decision

_PAYLOAD = '{"classification": "command", "cleaned_text": "open firefox", "reason": "direct"}'


def test_parses_plain_json() -> None:
    result, reason = parse_gate_result(_PAYLOAD)
    assert result.classification == "command"
    assert result.cleaned_command == "open firefox"
    assert reason == "direct"


def test_parses_fenced_json() -> None:
    result, _ = parse_gate_result(f"```json\n{_PAYLOAD}\n```")
    assert result.classification == "command"


def test_parses_uppercase_fence_tag() -> None:
    result, _ = parse_gate_result(f"```JSON\n{_PAYLOAD}\n```")
    assert result.classification == "command"


def test_parses_fence_with_surrounding_prose() -> None:
    result, _ = parse_gate_result(f"Sure, here it is:\n```json\n{_PAYLOAD}\n```\nLet me know!")
    assert result.classification == "command"


def test_parses_json_embedded_in_prose() -> None:
    result, _ = parse_gate_result(f"The classification is {_PAYLOAD} based on context.")
    assert result.cleaned_command == "open firefox"


def test_parses_list_wrapped_json() -> None:
    result, _ = parse_gate_result(f"[{_PAYLOAD}]")
    assert result.classification == "command"


def test_parses_arguments_wrapped_json() -> None:
    result, _ = parse_gate_result(f'{{"arguments": {_PAYLOAD}}}')
    assert result.classification == "command"


def test_parses_json_after_non_json_braces() -> None:
    result, _ = parse_gate_result(f"Consider {{x}} then {_PAYLOAD}")
    assert result.cleaned_command == "open firefox"


def test_parses_recovery_decision_embedded_in_prose() -> None:
    decision = parse_recovery_decision('Decision: {"action": "recover", "candidate_id": "u2", "reason": "match"} done.')
    assert decision.action == "recover"
    assert decision.candidate_id == "u2"


def test_parses_intent_refrain() -> None:
    payload = '{"classification": "command", "cleaned_text": "open firefox", "intent": "Opening Firefox"}'
    result, _ = parse_gate_result(payload)
    assert result.intent == "Opening Firefox"


def test_intent_absent_defaults_empty() -> None:
    result, _ = parse_gate_result(_PAYLOAD)
    assert result.intent == ""
