import types

from tusk.kernel.api import KernelAPI
from tusk.shared.schemas.kernel_response import KernelResponse


def test_kernel_api_routes_text_to_dictation_mode() -> None:
    result, actions = _submit("hello world")
    assert result == KernelResponse(True, "updated")
    assert actions == ["process:hello world"]


def test_kernel_api_uses_command_mode_when_not_in_dictation() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    result = api.submit("some command")
    assert result == KernelResponse(True, "some command")


def test_request_dictation_stop_calls_mode_stop() -> None:
    actions: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api._dictation_mode = _dictation_mode(actions)
    result = api.request_dictation_stop()
    assert result == KernelResponse(True, "stopped")
    assert "stop" in actions


def test_request_dictation_stop_is_noop_when_not_in_dictation() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    result = api.request_dictation_stop()
    assert result == KernelResponse(False, "")


def test_start_dictation_calls_on_start_callback() -> None:
    called = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api.set_dictation_callbacks(on_start=lambda: called.append("start"), on_stop=lambda: None)
    api.start_dictation(_state())
    assert called == ["start"]


def test_stop_dictation_calls_on_stop_callback() -> None:
    called = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api.set_dictation_callbacks(on_start=lambda: None, on_stop=lambda: called.append("stop"))
    api.start_dictation(_state())
    api.stop_dictation()
    assert called == ["stop"]


def _submit(text: str) -> tuple[KernelResponse, list[str]]:
    actions: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api._dictation_mode = _dictation_mode(actions)
    return api.submit(text), actions


def _command_mode() -> object:
    return types.SimpleNamespace(process_command=lambda text: KernelResponse(True, text))


def _dictation_mode(actions: list[str]) -> object:
    return types.SimpleNamespace(
        stop=lambda: actions.append("stop") or KernelResponse(True, "stopped"),
        process_text=lambda text: actions.append(f"process:{text}") or KernelResponse(True, "updated"),
    )


def _state() -> object:
    return types.SimpleNamespace()
