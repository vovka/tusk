from tusk.kernel.dictation_gate_prompt import DICTATION_GATE_PROMPT


def test_dictation_gate_prompt_limits_commands_to_stop() -> None:
    assert "only command you may detect is a request to stop dictation" in DICTATION_GATE_PROMPT
    assert "Everything else must be treated as literal dictation text" in DICTATION_GATE_PROMPT


def test_dictation_gate_prompt_uses_dictation_schema() -> None:
    assert "metadata_stop" in DICTATION_GATE_PROMPT
