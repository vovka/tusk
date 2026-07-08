import types

import pytest

from tusk.kernel.modes.coding_gate_prompt import CODING_GATE_PROMPT
from tusk.kernel.modes.dictation_gate_prompt import DICTATION_GATE_PROMPT
from tusk.kernel.modes.mode_gate import ModeGate

_MODES = [("dictation", DICTATION_GATE_PROMPT), ("coding", CODING_GATE_PROMPT)]


@pytest.mark.parametrize("mode_name,prompt", _MODES)
def test_gate_stops_when_llm_marks_metadata_stop(mode_name, prompt) -> None:
    gate = ModeGate(_llm(_stop_json()), mode_name, prompt, _log())
    assert gate.should_stop("okay tusk, stop now") is True


@pytest.mark.parametrize("mode_name,prompt", _MODES)
def test_gate_keeps_text_when_llm_declines_stop(mode_name, prompt) -> None:
    gate = ModeGate(_llm(_literal_json()), mode_name, prompt, _log())
    assert gate.should_stop("the word stop appears mid-sentence") is False


@pytest.mark.parametrize("mode_name,prompt", _MODES)
def test_gate_falls_back_to_plain_completion(mode_name, prompt) -> None:
    gate = ModeGate(_fallback_llm(), mode_name, prompt, _log())
    assert gate.should_stop("please stop now") is True


@pytest.mark.parametrize("mode_name,prompt", _MODES)
def test_gate_sends_mode_specific_prompt_and_schema(mode_name, prompt) -> None:
    captured: dict[str, object] = {}

    def structured(system_prompt, text, name, schema, max_tokens):
        captured.update(prompt=system_prompt, name=name)
        return _stop_json()

    gate = ModeGate(types.SimpleNamespace(label="gate", complete_structured=structured), mode_name, prompt, _log())
    gate.should_stop("stop")
    assert captured["prompt"] == prompt
    assert captured["name"] == f"{mode_name}_gatekeeper"


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
