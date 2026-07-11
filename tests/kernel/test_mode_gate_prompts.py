from tusk.kernel.modes.coding_gate_prompt import CODING_GATE_PROMPT
from tusk.kernel.modes.dictation_gate_prompt import DICTATION_GATE_PROMPT


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
