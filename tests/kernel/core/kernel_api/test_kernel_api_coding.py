import types

from tusk.kernel.core.kernel_api import KernelAPI
from tusk.kernel.modes.mode_state import ModeState
from tusk.shared.schemas.kernel_response import KernelResponse


def test_submit_routes_text_to_coding_mode_when_active() -> None:
    actions: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    _start_coding(api, actions)
    result = api.submit("add a loop")
    assert result == KernelResponse(True, "updated")
    assert actions == ["process:add a loop"]


def test_coding_mode_takes_precedence_over_command_mode() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    assert api.submit("plain command") == KernelResponse(True, "plain command")
    _start_coding(api, [])
    assert api.submit("edit").reply == "updated"


def test_request_coding_stop_calls_router_stop_with_state() -> None:
    actions: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    _start_coding(api, actions)
    assert api.coding.request_stop() == KernelResponse(True, "stopped")
    assert actions == ["stop:s1"]
    assert api.coding.active is False


def test_request_coding_stop_is_noop_when_not_coding() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    assert api.coding.request_stop() == KernelResponse(False, "")


def test_coding_active_reflects_mode_state() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    assert api.coding.active is False
    _start_coding(api, [])
    assert api.coding.active is True


def test_start_and_stop_coding_fire_callbacks() -> None:
    called: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api.coding.set_callbacks(on_start=lambda: called.append("start"), on_stop=lambda: called.append("stop"))
    api.coding.start(_state())
    api.coding.stop()
    assert called == ["start", "stop"]


def _command_mode() -> object:
    return types.SimpleNamespace(process_command=lambda text, kind="conversation": KernelResponse(True, text))


def _start_coding(api: KernelAPI, actions: list[str]) -> None:
    api.coding.attach_mode(types.SimpleNamespace(
        stop=lambda state: actions.append(f"stop:{state.session_id}") or KernelResponse(True, "stopped"),
        process=lambda state, text: actions.append(f"process:{text}") or KernelResponse(True, "updated"),
    ))
    api.coding.start(_state())


def _state() -> ModeState:
    return ModeState("coding", "s1", "gnome")


def test_mode_bypass_kind_reaches_command_mode_while_coding() -> None:
    kinds: list[str] = []
    command_mode = types.SimpleNamespace(process_command=lambda text, kind: kinds.append(kind) or KernelResponse(True, text))
    api = KernelAPI(command_mode, types.SimpleNamespace())
    _start_coding(api, actions := [])
    assert api.submit("use gpt oss", "mode-bypass:command") == KernelResponse(True, "use gpt oss")
    assert kinds == ["command"] and actions == []
