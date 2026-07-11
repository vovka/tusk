from tusk.shared.tracing.interfaces.span_handle import SpanHandle

__all__ = ["OTelSpanHandle"]


class OTelSpanHandle(SpanHandle):
    def __init__(self, otel_span: object) -> None:
        self._span = otel_span

    def set_attribute(self, key: str, value: str) -> None:
        self._span.set_attribute(key, value)
