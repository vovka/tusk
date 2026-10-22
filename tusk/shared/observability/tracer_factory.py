import atexit
from typing import TYPE_CHECKING

from tusk.shared.interfaces.tracer import Tracer
from tusk.shared.observability.null_tracer import NullTracer
from tusk.shared.observability.otel_tracer import OTelTracer

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer as OTelSDKTracer

__all__ = ["TracerFactory"]


class TracerFactory:
    def create(self, otlp_endpoint: str, service_name: str = "tusk") -> Tracer:
        if not otlp_endpoint:
            return NullTracer()
        return OTelTracer(self._build_otel_tracer(otlp_endpoint, service_name))

    def _build_otel_tracer(self, otlp_endpoint: str, service_name: str) -> "OTelSDKTracer":
        # imported lazily so the SDK is only required when tracing is enabled
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
        # flush spans still buffered in the batch processor when the app exits
        atexit.register(provider.shutdown)
        return provider.get_tracer(service_name)
