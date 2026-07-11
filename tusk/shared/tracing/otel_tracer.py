from collections.abc import Iterator
from contextlib import contextmanager

from tusk.shared.tracing.interfaces.span_handle import SpanHandle
from tusk.shared.tracing.interfaces.tracer import Tracer
from tusk.shared.tracing.otel_span_handle import OTelSpanHandle

__all__ = ["OTelTracer"]


class OTelTracer(Tracer):
    def __init__(self, otel_tracer: object) -> None:
        self._tracer = otel_tracer

    @contextmanager
    def span(self, name: str, attributes: dict[str, str]) -> Iterator[SpanHandle]:
        with self._tracer.start_as_current_span(name, attributes=attributes) as otel_span:
            yield OTelSpanHandle(otel_span)
