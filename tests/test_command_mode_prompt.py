from shells.voice.stages.command_gate_prompt import build_command_gate_prompt


def test_command_mode_prompt_treats_wake_word_as_addressing_not_command() -> None:
    prompt = build_command_gate_prompt("")
    assert "Wake words only show the user is addressing TUSK." in prompt
    assert "Do not treat wake-word presence alone as a command." in prompt


def test_follow_up_prompt_mentions_recent_context() -> None:
    prompt = build_command_gate_prompt("User: open Firefox")
    assert "Follow-up utterances may omit the wake word." in prompt
    assert "Recent context:" in prompt
