from collections.abc import Iterator
from contextlib import contextmanager

from tusk.shared.interfaces.span_handle import SpanHandle
from tusk.shared.interfaces.tracer import Tracer
from tusk.shared.observability.null_span_handle import NullSpanHandle

__all__ = ["NullTracer"]


class NullTracer(Tracer):
    @contextmanager
    def span(self, name: str, attributes: dict[str, str]) -> Iterator[SpanHandle]:
        yield NullSpanHandle()
