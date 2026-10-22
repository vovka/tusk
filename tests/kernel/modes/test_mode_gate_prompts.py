from tusk.kernel.modes.mode_gate_prompts import CODING_GATE_PROMPT, DICTATION_GATE_PROMPT


def test_coding_gate_prompt_requires_unambiguous_stop_intent() -> None:
    assert "sole, unambiguous meaning" in CODING_GATE_PROMPT
    assert "any doubt" in CODING_GATE_PROMPT


def test_coding_gate_prompt_names_editing_commands_as_negative_examples() -> None:
    assert "remove the first three lines" in CODING_GATE_PROMPT
    assert "never stop requests" in CODING_GATE_PROMPT


def test_coding_gate_prompt_excludes_self_talk() -> None:
    assert "I'm going to go" in CODING_GATE_PROMPT


def test_dictation_gate_prompt_requires_unambiguous_stop_intent() -> None:
    assert "sole, unambiguous meaning" in DICTATION_GATE_PROMPT
    assert "any doubt" in DICTATION_GATE_PROMPT


def test_dictation_gate_prompt_treats_mentions_of_stopping_as_text() -> None:
    assert "merely mention stopping" in DICTATION_GATE_PROMPT


def test_dictation_gate_prompt_limits_commands_to_stop() -> None:
    assert "only command you may detect is a request to stop dictation" in DICTATION_GATE_PROMPT
    assert "Everything else must be treated as literal dictation text" in DICTATION_GATE_PROMPT


def test_dictation_gate_prompt_uses_dictation_schema() -> None:
    assert "metadata_stop" in DICTATION_GATE_PROMPT
