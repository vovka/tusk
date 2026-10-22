from tusk.shared.observability.null_tracer import NullTracer


def test_null_tracer_span_is_usable_context_manager() -> None:
    with NullTracer().span("kernel.request", {"request_id": "abc"}) as span:
        span.set_attribute("response_preview", "hello")
