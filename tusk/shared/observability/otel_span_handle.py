from typing import TYPE_CHECKING

from tusk.shared.interfaces.span_handle import SpanHandle

if TYPE_CHECKING:
    from opentelemetry.trace import Span

__all__ = ["OTelSpanHandle"]


class OTelSpanHandle(SpanHandle):
    def __init__(self, otel_span: "Span") -> None:
        self._span = otel_span

    def set_attribute(self, key: str, value: str) -> None:
        self._span.set_attribute(key, value)
