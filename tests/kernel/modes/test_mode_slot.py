import types

import pytest

from tusk.kernel.modes.mode_slot import ModeSlot
from tusk.kernel.modes.mode_state import ModeState
from tusk.shared.schemas.app_mode import AppMode
from tusk.shared.schemas.kernel_response import KernelResponse


def _slot(reporter: object | None = None, logs: list[tuple] | None = None) -> ModeSlot:
    log = types.SimpleNamespace(log=lambda *args: logs.append(args) if logs is not None else None)
    return ModeSlot(AppMode.DICTATION, "Dictation started.", log, reporter)


def _state() -> ModeState:
    return ModeState("dictation", "s1", "gnome")


def _mode(seen: list) -> object:
    return types.SimpleNamespace(
        process=lambda state, text: seen.append((state, text)) or KernelResponse(True, "updated"),
        stop=lambda state: seen.append(("stop", state)) or KernelResponse(True, "Dictation stopped."),
    )


def test_start_activates_and_replies_with_mode_reply() -> None:
    slot = _slot()
    response = slot.start(_state())
    assert response == KernelResponse(True, "Dictation started.")
    assert slot.active is True


def test_callbacks_fire_on_start_and_stop() -> None:
    called: list[str] = []
    slot = _slot()
    slot.set_callbacks(lambda: called.append("start"), lambda: called.append("stop"))
    slot.start(_state())
    slot.stop()
    assert called == ["start", "stop"]
    assert slot.active is False


def test_start_and_stop_report_app_mode() -> None:
    modes: list[AppMode] = []
    slot = _slot(types.SimpleNamespace(set_mode=modes.append))
    slot.start(_state())
    slot.stop()
    assert modes == [AppMode.DICTATION, AppMode.DEFAULT]


def test_request_stop_without_active_mode_reports_unhandled() -> None:
    assert _slot().request_stop() == KernelResponse(False, "")


def test_process_text_without_active_mode_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError):
        _slot().process_text("hello")


def test_process_text_routes_state_and_text_through_attached_mode() -> None:
    seen: list[tuple] = []
    slot = _slot()
    slot.attach_mode(_mode(seen))
    slot.start(_state())
    assert slot.process_text("hello") == KernelResponse(True, "updated")
    assert seen == [(_state(), "hello")]


def test_process_text_logs_reply_under_mode_tag() -> None:
    logs: list[tuple] = []
    slot = _slot(logs=logs)
    slot.attach_mode(_mode([]))
    slot.start(_state())
    slot.process_text("x")
    assert logs == [("DICTATION", "updated")]


def test_request_stop_stops_mode_then_slot() -> None:
    seen: list[tuple] = []
    slot = _slot()
    slot.attach_mode(_mode(seen))
    slot.start(_state())
    assert slot.request_stop() == KernelResponse(True, "Dictation stopped.")
    assert seen == [("stop", _state())]
    assert slot.active is False


def test_request_stop_logs_always_visible_mode_ended_line() -> None:
    # E2E: a bare "stop pair coding mode" left the mode with nothing in the default log
    from tusk.shared.logging.log_tag_palette import is_always_visible
    logs: list[tuple] = []
    slot = _slot(logs=logs)
    slot.attach_mode(_mode([]))
    slot.start(_state())
    slot.request_stop()
    assert ("DICTATION", "Dictation stopped.") in logs
    assert ("MODE", "dictation mode ended") in logs
    assert is_always_visible("MODE")
