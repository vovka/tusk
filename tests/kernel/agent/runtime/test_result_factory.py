import pytest

from tusk.kernel.agent.runtime.result_factory import ResultFactory


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ("HTTP 429 rate limit", "rate limited"),
        ("json_validate_failed", "reliable plan"),
        ("tool_use_failed", "invalid tool call"),
        ("empty completion", "empty response"),
        ("provider down", "temporarily unavailable"),
    ],
)
def test_model_failure_text_maps_error_class_to_reply(error: str, expected: str) -> None:
    assert expected in ResultFactory(None).model_failure_text(RuntimeError(error))
