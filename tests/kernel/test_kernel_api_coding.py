import types

from tusk.kernel.core.kernel_api import KernelAPI
from tusk.shared.schemas.kernel_response import KernelResponse


def test_submit_routes_text_to_coding_mode_when_active() -> None:
    actions: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api._coding._mode = _coding_mode(actions)
    result = api.submit("add a loop")
    assert result == KernelResponse(True, "updated")
    assert actions == ["process:add a loop"]


def test_coding_mode_takes_precedence_over_command_mode() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    assert api.submit("plain command") == KernelResponse(True, "plain command")
    api._coding._mode = _coding_mode([])
    assert api.submit("edit").reply == "updated"


def test_request_coding_stop_calls_mode_stop() -> None:
    actions: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api._coding._mode = _coding_mode(actions)
    assert api.request_coding_stop() == KernelResponse(True, "stopped")
    assert "stop" in actions


def test_request_coding_stop_is_noop_when_not_coding() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    assert api.request_coding_stop() == KernelResponse(False, "")


def test_coding_active_reflects_mode_state() -> None:
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    assert api.coding_active is False
    api._coding._mode = _coding_mode([])
    assert api.coding_active is True


def test_start_and_stop_coding_fire_callbacks() -> None:
    called: list[str] = []
    api = KernelAPI(_command_mode(), types.SimpleNamespace())
    api.set_coding_callbacks(on_start=lambda: called.append("start"), on_stop=lambda: called.append("stop"))
    api.start_coding(types.SimpleNamespace())
    api.stop_coding()
    assert called == ["start", "stop"]


def _command_mode() -> object:
    return types.SimpleNamespace(process_command=lambda text, kind="conversation": KernelResponse(True, text))


def _coding_mode(actions: list[str]) -> object:
    return types.SimpleNamespace(
        stop=lambda: actions.append("stop") or KernelResponse(True, "stopped"),
        process_text=lambda text: actions.append(f"process:{text}") or KernelResponse(True, "updated"),
    )
