import types

import pytest

from tusk.kernel.adapter_mode import AdapterMode
from tusk.kernel.coding_state import CodingState
from tusk.shared.schemas.kernel_response import KernelResponse


@pytest.mark.parametrize("tag", ["DICTATION", "CODING"])
def test_process_text_delegates_to_router_with_state(tag: str) -> None:
    seen: list[tuple[object, str]] = []
    mode = AdapterMode(_state(), _router(seen), _log(), tag)
    result = mode.process_text("add a guard clause")
    assert result == KernelResponse(True, "updated")
    assert seen == [(mode.state, "add a guard clause")]


def test_stop_delegates_to_router() -> None:
    mode = AdapterMode(_state(), _stopping_router(), _log(), "CODING")
    assert mode.stop() == KernelResponse(True, "Coding stopped.")


def test_logs_under_mode_tag() -> None:
    logs: list[tuple] = []
    log = types.SimpleNamespace(log=lambda *args: logs.append(args))
    AdapterMode(_state(), _router([]), log, "DICTATION").process_text("x")
    assert logs == [("DICTATION", "updated")]


def _state() -> CodingState:
    return CodingState("coding", "s1", "gnome")


def _router(seen: list) -> object:
    return types.SimpleNamespace(process=lambda state, text: seen.append((state, text)) or KernelResponse(True, "updated"))


def _stopping_router() -> object:
    return types.SimpleNamespace(stop=lambda state: KernelResponse(True, "Coding stopped."))


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
