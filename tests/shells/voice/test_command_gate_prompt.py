from shells.voice.stages.gate.command_gate_prompt import build_command_gate_prompt


def test_command_gate_prompt_requests_intent_refrain() -> None:
    prompt = build_command_gate_prompt("")
    assert '"intent"' in prompt


def test_busy_clause_requires_unambiguous_stop_intent() -> None:
    prompt = build_command_gate_prompt("", busy=True)
    assert "sole, unambiguous meaning" in prompt
    assert "any doubt" in prompt


def test_busy_clause_excludes_self_talk_from_interrupts() -> None:
    prompt = build_command_gate_prompt("", busy=True)
    assert "I'm going to go" in prompt
    assert "not an interrupt" in prompt
