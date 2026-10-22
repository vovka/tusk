import tusk.shared.observability as observability

_TRACING = {"NullSpanHandle", "NullTracer", "OTelSpanHandle", "OTelTracer", "TracerFactory"}
_LOG_AND_STATUS = {"ColorLogPrinter", "LatencyMeter", "NullStatusSink", "StatusReporter"}


def test_shared_observability_exports_present() -> None:
    assert set(observability.__all__) == _TRACING | _LOG_AND_STATUS
