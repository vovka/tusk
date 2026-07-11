from tusk.shared.tracing.interfaces.span_handle import SpanHandle

__all__ = ["RecordingSpanHandle"]


class RecordingSpanHandle(SpanHandle):
    def __init__(self, record: dict[str, object]) -> None:
        self._record = record

    def set_attribute(self, key: str, value: str) -> None:
        self._record["attributes"][key] = value
