import types

from shells.voice.gate_dispatch import GateDispatch
from shells.voice.gatekeeper_slot import GatekeeperSlot


def _gatekeeper(action: str, text: str = "hi") -> object:
    return types.SimpleNamespace(
        process=lambda u, r, candidates=None: GateDispatch(action, text),
        evaluate=lambda u, r: f"eval:{action}",
    )


def test_gatekeeper_slot_delegates_process_to_inner() -> None:
    slot = GatekeeperSlot(_gatekeeper("forward_current", "hello"))
    result = slot.process(None, [])
    assert result == GateDispatch("forward_current", "hello")


def test_gatekeeper_slot_delegates_evaluate_to_inner() -> None:
    slot = GatekeeperSlot(_gatekeeper("drop"))
    assert slot.evaluate(None, []) == "eval:drop"


def test_gatekeeper_slot_swap_changes_delegate() -> None:
    slot = GatekeeperSlot(_gatekeeper("drop"))
    slot.swap(_gatekeeper("forward_current", "new"))
    assert slot.process(None, []) == GateDispatch("forward_current", "new")


def test_gatekeeper_slot_swap_does_not_affect_original() -> None:
    original = _gatekeeper("drop")
    slot = GatekeeperSlot(original)
    slot.swap(_gatekeeper("forward_current", "swapped"))
    assert original.process(None, []) == GateDispatch("drop", "hi")
