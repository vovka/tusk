from tusk.shared.tracing.interfaces.span_handle import SpanHandle

__all__ = ["NullSpanHandle"]


class NullSpanHandle(SpanHandle):
    def set_attribute(self, key: str, value: str) -> None:
        return None
