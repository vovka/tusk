from contextlib import contextmanager
from collections.abc import Iterator

from tests.recording_span_handle import RecordingSpanHandle
from tusk.shared.tracing.interfaces.span_handle import SpanHandle
from tusk.shared.tracing.interfaces.tracer import Tracer

__all__ = ["RecordingTracer"]


class RecordingTracer(Tracer):
    def __init__(self) -> None:
        self.spans: list[dict[str, object]] = []
        self._depth = 0

    @contextmanager
    def span(self, name: str, attributes: dict[str, str]) -> Iterator[SpanHandle]:
        record = {"name": name, "attributes": dict(attributes), "depth": self._depth}
        self.spans.append(record)
        self._depth += 1
        try:
            yield RecordingSpanHandle(record)
        finally:
            self._depth -= 1
