from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from tusk.shared.interfaces.span_handle import SpanHandle
from tusk.shared.interfaces.tracer import Tracer
from tusk.shared.observability.otel_span_handle import OTelSpanHandle

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer as OTelSDKTracer

__all__ = ["OTelTracer"]


class OTelTracer(Tracer):
    def __init__(self, otel_tracer: "OTelSDKTracer") -> None:
        self._tracer = otel_tracer

    @contextmanager
    def span(self, name: str, attributes: dict[str, str]) -> Iterator[SpanHandle]:
        with self._tracer.start_as_current_span(name, attributes=attributes) as otel_span:
            yield OTelSpanHandle(otel_span)
