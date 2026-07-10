from shells.voice.stages.gate.command_gate_prompt import build_command_gate_prompt


def test_command_gate_prompt_requests_intent_refrain() -> None:
    prompt = build_command_gate_prompt("")
    assert '"intent"' in prompt
