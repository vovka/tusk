import tusk.shared.tracing.tracer_factory as tracer_factory_module
from tusk.shared.tracing.null_tracer import NullTracer
from tusk.shared.tracing.otel_tracer import OTelTracer
from tusk.shared.tracing.tracer_factory import TracerFactory


def test_factory_returns_null_tracer_without_endpoint() -> None:
    assert isinstance(TracerFactory().create(""), NullTracer)


def test_factory_flushes_spans_at_exit(monkeypatch) -> None:
    registered: list[object] = []
    monkeypatch.setattr(tracer_factory_module.atexit, "register", registered.append)
    TracerFactory().create("http://phoenix:6006/v1/traces")
    # lazy OTel imports register their own atexit hooks; only ours matters here
    assert "shutdown" in [callback.__name__ for callback in registered]


def test_factory_returns_otel_tracer_with_endpoint() -> None:
    tracer = TracerFactory().create("http://phoenix:6006/v1/traces")
    assert isinstance(tracer, OTelTracer)
