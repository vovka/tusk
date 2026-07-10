import types

from tests.recording_tracer import RecordingTracer
from tusk.shared.llm.llm_proxy import LLMProxy


def _provider() -> object:
    return types.SimpleNamespace(
        label="groq/test-model",
        complete=lambda system_prompt, user_message, max_tokens=256: "fine, thanks",
    )


def test_proxy_wraps_llm_call_in_named_span() -> None:
    tracer = RecordingTracer()
    proxy = LLMProxy(_provider(), slot_name="gatekeeper", tracer=tracer)
    proxy.complete("system", "hello")
    assert tracer.spans[0]["name"] == "llm.gatekeeper"
    attributes = tracer.spans[0]["attributes"]
    assert attributes["provider"] == "groq/test-model"
    assert attributes["kind"] == "complete"


def test_proxy_records_response_preview_on_span() -> None:
    tracer = RecordingTracer()
    proxy = LLMProxy(_provider(), slot_name="gatekeeper", tracer=tracer)
    proxy.complete("system", "hello")
    assert tracer.spans[0]["attributes"]["response_preview"] == "fine, thanks"


def test_proxy_without_tracer_still_completes() -> None:
    proxy = LLMProxy(_provider(), slot_name="gatekeeper")
    assert proxy.complete("system", "hello") == "fine, thanks"
