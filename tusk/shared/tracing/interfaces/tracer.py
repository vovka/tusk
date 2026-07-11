from abc import ABC, abstractmethod
from contextlib import AbstractContextManager

from tusk.shared.tracing.interfaces.span_handle import SpanHandle

__all__ = ["Tracer"]


class Tracer(ABC):
    @abstractmethod
    def span(self, name: str, attributes: dict[str, str]) -> AbstractContextManager[SpanHandle]:
        ...
