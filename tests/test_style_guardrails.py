from pathlib import Path

from tests.style_guardrails.directory_guardrails import DirectoryGuardrails
from tests.style_guardrails.file_guardrails import FileGuardrails
from tests.style_guardrails.function_guardrails import FunctionGuardrails


def _write_offender(root: Path) -> None:
    hidden = root / ".hidden"
    hidden.mkdir()
    lines = ["def big() -> None:", *[f"    x{i} = {i}" for i in range(150)]]
    (hidden / "big.py").write_text("\n".join(lines) + "\n")


def test_python_files_stay_within_size_limits() -> None:
    assert FileGuardrails().violations() == []


def test_python_functions_stay_small() -> None:
    assert FunctionGuardrails().violations() == []


def test_directories_stay_within_file_and_depth_limits() -> None:
    assert DirectoryGuardrails().violations() == []


def test_directory_guardrails_flag_oversized_directory(tmp_path) -> None:
    package = tmp_path / "tusk" / "big"
    package.mkdir(parents=True)
    for index in range(13):
        (package / f"module_{index}.py").write_text("x = 1\n")
    violations = DirectoryGuardrails(tmp_path).violations()
    assert violations == [f"{Path('tusk') / 'big'}: 13 python files (max 12)"]


def test_directory_guardrails_flag_too_deep_package(tmp_path) -> None:
    package = tmp_path / "tusk" / "a" / "b" / "c" / "d" / "e"
    package.mkdir(parents=True)
    (package / "module.py").write_text("x = 1\n")
    violations = DirectoryGuardrails(tmp_path).violations()
    assert violations == [f"{package.relative_to(tmp_path)}: package depth 6 (max 5)"]


def test_directory_guardrails_flag_oversized_tests_directory(tmp_path) -> None:
    package = tmp_path / "tests" / "big"
    package.mkdir(parents=True)
    for index in range(13):
        (package / f"test_{index}.py").write_text("x = 1\n")
    violations = DirectoryGuardrails(tmp_path).violations()
    assert violations == [f"{Path('tests') / 'big'}: 13 python files (max 12)"]


def test_file_guardrails_skip_hidden_directories(tmp_path: Path) -> None:
    _write_offender(tmp_path)
    assert FileGuardrails(tmp_path).violations() == []


def test_function_guardrails_skip_hidden_directories(tmp_path: Path) -> None:
    _write_offender(tmp_path)
    assert FunctionGuardrails(tmp_path).violations() == []
