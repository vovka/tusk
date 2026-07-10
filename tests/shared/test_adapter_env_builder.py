import os
from pathlib import Path

from tusk.shared.mcp import AdapterEnvironmentBuilder

_REPO_ROOT = str(Path(__file__).resolve().parents[2])


def test_base_env_prepends_repo_root_to_pythonpath(monkeypatch) -> None:
    monkeypatch.setenv("PYTHONPATH", "/existing")
    env = AdapterEnvironmentBuilder(".tusk_runtime/adapters").base_env()
    assert env["PYTHONPATH"] == f"{_REPO_ROOT}{os.pathsep}/existing"


def test_base_env_sets_pythonpath_when_absent(monkeypatch) -> None:
    monkeypatch.delenv("PYTHONPATH", raising=False)
    env = AdapterEnvironmentBuilder(".tusk_runtime/adapters").base_env()
    assert env["PYTHONPATH"] == _REPO_ROOT


def test_build_without_requirements_keeps_repo_root_pythonpath(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PYTHONPATH", raising=False)
    env = AdapterEnvironmentBuilder(str(tmp_path / "cache")).build(tmp_path, {"name": "demo", "version": "1"})
    assert env["PYTHONPATH"] == _REPO_ROOT
