import types

from tusk.kernel.coding_mode import AdapterCodingMode
from tusk.kernel.coding_state import CodingState
from tusk.shared.schemas.kernel_response import KernelResponse


def test_process_text_delegates_to_router_with_state() -> None:
    seen: list[tuple[object, str]] = []
    mode = AdapterCodingMode(_state(), _router(seen), _log())
    result = mode.process_text("add a guard clause")
    assert result == KernelResponse(True, "updated")
    assert seen == [(mode.state, "add a guard clause")]


def test_stop_delegates_to_router() -> None:
    mode = AdapterCodingMode(_state(), _stopping_router(), _log())
    assert mode.stop() == KernelResponse(True, "Coding stopped.")


def _state() -> CodingState:
    return CodingState("coding", "s1", "gnome")


def _router(seen: list) -> object:
    return types.SimpleNamespace(process=lambda state, text: seen.append((state, text)) or KernelResponse(True, "updated"))


def _stopping_router() -> object:
    return types.SimpleNamespace(stop=lambda state: KernelResponse(True, "Coding stopped."))


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
