import types

from shells.voice.stages.coding_gatekeeper import CodingGatekeeper


def test_forwards_text_as_coding_instruction_when_not_stopping() -> None:
    gatekeeper = CodingGatekeeper(_gate(False), lambda: None, _log())
    dispatch = gatekeeper.process(_utterance("add a method"), [])
    assert dispatch.action == "forward_current"
    assert dispatch.text == "add a method"


def test_drops_and_stops_when_gate_detects_stop() -> None:
    stopped: list[bool] = []
    gatekeeper = CodingGatekeeper(_gate(True), lambda: stopped.append(True), _log())
    dispatch = gatekeeper.process(_utterance("stop coding"), [])
    assert dispatch.action == "drop"
    assert stopped == [True]


def _gate(should_stop: bool) -> object:
    return types.SimpleNamespace(should_stop=lambda text: should_stop)


def _utterance(text: str) -> object:
    return types.SimpleNamespace(text=text)


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
