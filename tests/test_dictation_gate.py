import types

from tusk.kernel.dictation_gate import DictationGate


def test_dictation_gate_stops_when_llm_marks_metadata_stop() -> None:
    gate = DictationGate(_llm(_stop_json()), _log())
    assert gate.should_stop("stop the dictation, please") is True


def test_dictation_gate_keeps_literal_text_when_llm_declines_stop() -> None:
    gate = DictationGate(_llm(_literal_json()), _log())
    assert gate.should_stop("stop dictation appears in the sentence") is False


def test_dictation_gate_falls_back_to_plain_completion() -> None:
    gate = DictationGate(_fallback_llm(), _log())
    assert gate.should_stop("please stop dictation now") is True


def _llm(response: str) -> object:
    return types.SimpleNamespace(label="gate", complete_structured=lambda *args: response)


def _fallback_llm() -> object:
    return types.SimpleNamespace(label="gate", complete_structured=_structured_failure, complete=lambda *args: _stop_json())


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)


def _stop_json() -> str:
    return '{"directed":true,"cleaned_command":"","metadata_stop":"user asked to stop"}'


def _literal_json() -> str:
    return '{"directed":false,"cleaned_command":"","metadata_stop":null}'


def _structured_failure(*args) -> str:
    raise RuntimeError("json_validate_failed")
