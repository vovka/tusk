from tusk.shared.tracing.null_tracer import NullTracer
from tusk.shared.tracing.otel_tracer import OTelTracer
from tusk.shared.tracing.tracer_factory import TracerFactory


def test_factory_returns_null_tracer_without_endpoint() -> None:
    assert isinstance(TracerFactory().create(""), NullTracer)


def test_factory_returns_otel_tracer_with_endpoint() -> None:
    tracer = TracerFactory().create("http://phoenix:6006/v1/traces")
    assert isinstance(tracer, OTelTracer)
