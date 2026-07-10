from pathlib import Path

from tests.style_guardrails.directory_guardrails import DirectoryGuardrails
from tests.style_guardrails.file_guardrails import FileGuardrails
from tests.style_guardrails.function_guardrails import FunctionGuardrails


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
