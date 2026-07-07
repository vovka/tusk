import types

import pytest

from tusk.kernel.mode_slot import ModeSlot
from tusk.shared.schemas.kernel_response import KernelResponse


def _slot() -> ModeSlot:
    return ModeSlot("DICTATION", "Dictation started.")


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)


def test_start_activates_and_replies_with_mode_reply() -> None:
    slot = _slot()
    response = slot.start(types.SimpleNamespace(), _log())
    assert response == KernelResponse(True, "Dictation started.")
    assert slot.active is True


def test_callbacks_fire_on_start_and_stop() -> None:
    called: list[str] = []
    slot = _slot()
    slot.set_callbacks(lambda: called.append("start"), lambda: called.append("stop"))
    slot.start(types.SimpleNamespace(), _log())
    slot.stop()
    assert called == ["start", "stop"]
    assert slot.active is False


def test_request_stop_without_active_mode_reports_unhandled() -> None:
    assert _slot().request_stop() == KernelResponse(False, "")


def test_process_text_without_active_mode_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError):
        _slot().process_text("hello")


def test_started_mode_routes_through_attached_router() -> None:
    seen: list[str] = []
    router = types.SimpleNamespace(process=lambda state, text: seen.append(text) or KernelResponse(True, "updated"))
    slot = _slot()
    slot.attach_router(router)
    slot.start(types.SimpleNamespace(), _log())
    assert slot.process_text("hello") == KernelResponse(True, "updated")
    assert seen == ["hello"]


def test_slot_uses_injected_mode_factory() -> None:
    created: list[tuple] = []

    def factory(state: object, router: object, log: object, tag: str) -> object:
        created.append((state, router, tag))
        return types.SimpleNamespace(process_text=lambda text: KernelResponse(True, "custom"))

    slot = ModeSlot("DICTATION", "Dictation started.", mode_factory=factory)
    slot.start(types.SimpleNamespace(), _log())
    assert created and created[0][2] == "DICTATION"
    assert slot.process_text("hi") == KernelResponse(True, "custom")
