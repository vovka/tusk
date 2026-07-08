from pathlib import Path

from tests.style_guardrails.file_guardrails import FileGuardrails
from tests.style_guardrails.function_guardrails import FunctionGuardrails


def _write_offender(root: Path) -> None:
    hidden = root / ".hidden"
    hidden.mkdir()
    lines = ["def big() -> None:", *[f"    x{i} = {i}" for i in range(150)]]
    (hidden / "big.py").write_text("\n".join(lines) + "\n")


def test_file_guardrails_skip_hidden_directories(tmp_path: Path) -> None:
    _write_offender(tmp_path)
    assert FileGuardrails(tmp_path).violations() == []


def test_function_guardrails_skip_hidden_directories(tmp_path: Path) -> None:
    _write_offender(tmp_path)
    assert FunctionGuardrails(tmp_path).violations() == []
