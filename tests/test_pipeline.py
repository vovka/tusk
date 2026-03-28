import types

from tusk.kernel.schemas.gate_result import GateResult
from tusk.kernel.pipeline import Pipeline
from tusk.kernel.schemas.kernel_response import KernelResponse


def test_pipeline_filters_hallucination_in_dictation_mode() -> None:
    calls: list[str] = []
    pipeline = Pipeline(_stt("Thank you."), _filter(calls, False), _gatekeeper(False), _command(), object(), object(), _log())
    pipeline.set_mode(_dictation(calls))
    result = pipeline.process_audio(b"audio", 16000)
    assert result.handled is False
    assert result.reply == ""
    assert calls == ["filter"]


def test_pipeline_stops_dictation_when_gatekeeper_marks_stop() -> None:
    calls: list[str] = []
    pipeline = Pipeline(_stt("Stop dictation mode"), _filter(calls, False), _gatekeeper(True), _command(), object(), object(), _log())
    pipeline.set_mode(_dictation(calls))
    result = pipeline.process_audio(b"audio", 16000)
    assert result.handled is True
    assert result.reply == "Dictation stopped."
    assert calls == ["stop"]


def test_pipeline_sends_non_stop_text_to_dictation_mode() -> None:
    calls: list[str] = []
    pipeline = Pipeline(_stt("Could you tell me a joke?"), _filter(calls, True), _gatekeeper(False), _command(), object(), object(), _log())
    pipeline.set_mode(_dictation(calls))
    result = pipeline.process_audio(b"audio", 16000)
    assert result.handled is True
    assert result.reply == "dictation updated"
    assert calls == ["filter", "dictation:Could you tell me a joke?"]


def _stt(text: str) -> object:
    utterance = types.SimpleNamespace(text=text, confidence=1.0, duration_seconds=1.0)
    return types.SimpleNamespace(transcribe=lambda audio, sample_rate: utterance)


def _filter(calls: list[str], valid: bool) -> object:
    return types.SimpleNamespace(is_valid=lambda utterance: calls.append("filter") or valid)


def _gatekeeper(stop: bool) -> object:
    metadata = {"metadata_stop": "stop"} if stop else {"metadata_stop": "None"}
    return types.SimpleNamespace(evaluate=lambda utterance, prompt: GateResult(stop, "", 1.0, metadata))


def _command() -> object:
    return types.SimpleNamespace(process_command=lambda text: KernelResponse(True, text), gatekeeper_prompt="", handle_gate_result=lambda gate: gate)


def _dictation(calls: list[str]) -> object:
    return types.SimpleNamespace(
        process_text=lambda text: calls.append(f"dictation:{text}") or KernelResponse(True, "dictation updated"),
        stop=lambda: calls.append("stop") or KernelResponse(True, "Dictation stopped."),
    )


def _log() -> object:
    return types.SimpleNamespace(log=lambda *args: None)
