import types

from composition.gatekeeper_builder import GatekeeperBuilder
from shells.voice.gate.playback_gate import PlaybackGate
from tusk.kernel.modes.mode_gate import ModeGate
from tusk.shared.interrupt_token import InterruptToken


def _config() -> types.SimpleNamespace:
    return types.SimpleNamespace(follow_up_timeout_seconds=30)


def _mode_kernel(requested: list[tuple]) -> types.SimpleNamespace:
    registry = types.SimpleNamespace(
        get=lambda name: requested.append(("get", name)) or object(),
        get_with_fallback=lambda name, fallback: requested.append(("fallback", name, fallback)) or object(),
    )
    return types.SimpleNamespace(
        llm_registry=registry, interrupt_token=InterruptToken(), submit=lambda text: None,
        dictation=_mode_slot(), coding=_mode_slot(),
    )


def _mode_slot() -> types.SimpleNamespace:
    return types.SimpleNamespace(set_callbacks=lambda on_start, on_stop: None, request_stop=lambda: None)


def _worker() -> types.SimpleNamespace:
    return types.SimpleNamespace(is_busy=False, current_speech_text=None)


def _builder(kernel: object) -> GatekeeperBuilder:
    return GatekeeperBuilder(_config(), kernel, types.SimpleNamespace(log=lambda *a: None))


def test_gatekeeper_wiring_resolves_stop_gate_slot_with_fallback() -> None:
    requested: list[tuple] = []
    slot = _builder(_mode_kernel(requested)).gatekeeper(_worker())
    assert ("get", "gatekeeper") in requested and ("fallback", "stop_gate", "gatekeeper") in requested
    assert isinstance(slot._inner, PlaybackGate)


def test_speech_stop_gate_client_has_no_fallback_completion() -> None:
    # the stop check runs while TUSK speaks; a second LLM round trip would delay the interrupt
    slot = _builder(_mode_kernel([])).gatekeeper(_worker())
    client = slot._inner._stop_gate._client
    assert client._allow_fallback is False and client._error_group == "speech-stop"


def test_mode_start_wires_the_mode_gate_stop_check_into_stop_gatekeeper() -> None:
    kernel, starts = _mode_kernel([]), []
    kernel.coding = types.SimpleNamespace(set_callbacks=lambda on_start, on_stop: starts.append(on_start), request_stop=lambda: None)
    slot = _builder(kernel).gatekeeper(_worker())
    starts[0]()
    assert slot._inner._inner._should_stop.__func__ is ModeGate.should_stop


def test_gatekeeper_tolerates_missing_registry() -> None:
    kernel = _mode_kernel([])
    kernel.llm_registry = None
    _builder(kernel).gatekeeper(_worker())
