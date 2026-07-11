from collections.abc import Iterator
from contextlib import contextmanager

from tusk.shared.tracing.interfaces.span_handle import SpanHandle
from tusk.shared.tracing.interfaces.tracer import Tracer
from tusk.shared.tracing.null_span_handle import NullSpanHandle

__all__ = ["NullTracer"]


class NullTracer(Tracer):
    @contextmanager
    def span(self, name: str, attributes: dict[str, str]) -> Iterator[SpanHandle]:
        yield NullSpanHandle()
