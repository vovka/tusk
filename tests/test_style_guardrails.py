from tests.style_guardrails.file_guardrails import FileGuardrails
from tests.style_guardrails.function_guardrails import FunctionGuardrails


def test_python_files_stay_within_size_limits() -> None:
    assert FileGuardrails().violations() == []


def test_python_functions_stay_small() -> None:
    assert FunctionGuardrails().violations() == []
