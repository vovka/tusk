import tusk.shared.tracing as tracing
import tusk.shared.tracing.interfaces as interfaces


def test_shared_tracing_exports_present() -> None:
    assert "NullTracer" in tracing.__all__
    assert "OTelTracer" in tracing.__all__
    assert "TracerFactory" in tracing.__all__
    assert "Tracer" in interfaces.__all__
    assert "SpanHandle" in interfaces.__all__
