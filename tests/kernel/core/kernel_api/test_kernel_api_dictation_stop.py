import types

from tusk.kernel.core.kernel_api import KernelAPI
from tusk.kernel.modes.mode_state import ModeState
from tusk.shared.schemas.kernel_response import KernelResponse


def test_kernel_api_routes_text_to_dictation_mode() -> None:
    result, actions = _submit("hello world")
    assert result == KernelResponse(True, "updated")
    assert actions == ["process:hello world"]


def test_kernel_api_uses_command_mode_when_not_in_dictation() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    result = api.submit("some command")
    assert result == KernelResponse(True, "some command")


def test_request_dictation_stop_calls_router_stop_with_state() -> None:
    actions: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    _start_dictation(api, actions)
    result = api.dictation.request_stop()
    assert result == KernelResponse(True, "stopped")
    assert actions == ["stop:s1"]
    assert api.dictation.active is False


def test_request_dictation_stop_is_noop_when_not_in_dictation() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    result = api.dictation.request_stop()
    assert result == KernelResponse(False, "")


def test_start_dictation_calls_on_start_callback() -> None:
    called = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api.dictation.set_callbacks(on_start=lambda: called.append("start"), on_stop=lambda: None)
    api.dictation.start(_state())
    assert called == ["start"]


def test_stop_dictation_calls_on_stop_callback() -> None:
    called = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api.dictation.set_callbacks(on_start=lambda: None, on_stop=lambda: called.append("stop"))
    api.dictation.start(_state())
    api.dictation.stop()
    assert called == ["stop"]


def _submit(text: str) -> tuple[KernelResponse, list[str]]:
    actions: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    _start_dictation(api, actions)
    return api.submit(text), actions


def _command_mode() -> object:
    return types.SimpleNamespace(process_command=lambda text, kind="conversation": KernelResponse(True, text))


def _start_dictation(api: KernelAPI, actions: list[str]) -> None:
    api.dictation.attach_mode(types.SimpleNamespace(
        stop=lambda state: actions.append(f"stop:{state.session_id}") or KernelResponse(True, "stopped"),
        process=lambda state, text: actions.append(f"process:{text}") or KernelResponse(True, "updated"),
    ))
    api.dictation.start(_state())


def _state() -> ModeState:
    return ModeState("dictation", "s1", "gnome")
