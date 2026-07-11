from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from tusk.shared.tracing.otel_tracer import OTelTracer


def _tracer_with_exporter() -> tuple[OTelTracer, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return OTelTracer(provider.get_tracer("tusk-tests")), exporter


def test_otel_tracer_records_span_with_attributes() -> None:
    tracer, exporter = _tracer_with_exporter()
    with tracer.span("llm.gatekeeper", {"kind": "structured"}) as span:
        span.set_attribute("response_preview", "ok")
    finished = exporter.get_finished_spans()
    assert finished[0].name == "llm.gatekeeper"
    assert finished[0].attributes["kind"] == "structured"
    assert finished[0].attributes["response_preview"] == "ok"


def test_otel_tracer_nests_child_spans_in_parent_trace() -> None:
    tracer, exporter = _tracer_with_exporter()
    with tracer.span("kernel.request", {}):
        with tracer.span("llm.conversation_agent", {}):
            pass
    child, parent = exporter.get_finished_spans()
    assert child.context.trace_id == parent.context.trace_id
    assert child.parent.span_id == parent.context.span_id
