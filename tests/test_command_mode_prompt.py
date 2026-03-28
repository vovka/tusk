import types

from tusk.kernel.command_mode import CommandMode


def test_command_mode_prompt_treats_wake_word_as_addressing_not_command() -> None:
    prompt = _mode().gatekeeper_prompt
    assert "Wake words only show the user is addressing TUSK." in prompt
    assert "Do not treat wake-word presence alone as a command." in prompt


def _mode() -> CommandMode:
    return CommandMode(_agent(), _clock(), _formatter(), _log())


def _agent() -> object:
    return types.SimpleNamespace(process_command=lambda command: None)


def _clock() -> object:
    return types.SimpleNamespace(is_within_follow_up_window=lambda: False)


def _formatter() -> object:
    return types.SimpleNamespace(format_recent_context=lambda: "")


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
