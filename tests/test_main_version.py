import sys

import pytest

import main
from tusk import __version__


def test_main_version_flag_prints_and_exits(monkeypatch, capsys) -> None:
    _prevent_startup(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["main.py", "--version"])
    with pytest.raises(SystemExit) as error:
        main.main()
    assert error.value.code == 0
    assert capsys.readouterr().out == __version__ + "\n"


def test_version_flag_combined_with_other_flags(monkeypatch, capsys) -> None:
    _prevent_startup(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["main.py", "--version", "--show-logs", "ready"])
    with pytest.raises(SystemExit) as error:
        main.main()
    assert error.value.code == 0
    assert capsys.readouterr().out == __version__ + "\n"


def test_main_normal_flow_without_version_flag(monkeypatch) -> None:
    started = []
    monkeypatch.setattr(sys, "argv", ["main.py"])
    monkeypatch.setattr(main.Config, "from_env", lambda: object())
    monkeypatch.setattr(main, "_build_log", lambda options: object())
    monkeypatch.setattr(main, "_build_tracer", lambda: object())
    monkeypatch.setattr(main, "StatusReporterHub", lambda sink, log: _reporter())
    monkeypatch.setattr(main, "_build_kernel", lambda *args: _kernel())
    monkeypatch.setattr(main, "ShellLoader", lambda *args: _loader(started))
    main.main()
    assert started == [True]


def _prevent_startup(monkeypatch) -> None:
    monkeypatch.setattr(main.Config, "from_env", _unexpected_startup)
    monkeypatch.setattr(main, "_build_log", _unexpected_startup)
    monkeypatch.setattr(main, "_build_tracer", _unexpected_startup)
    monkeypatch.setattr(main, "_build_kernel", _unexpected_startup)
    monkeypatch.setattr(main, "ShellLoader", _unexpected_startup)


def _unexpected_startup(*args) -> None:
    raise AssertionError("startup must not run for --version")


def _reporter() -> object:
    return type("Reporter", (), {"set_models": lambda self, models: None})()


def _kernel() -> object:
    registry = type("Registry", (), {"model_labels": lambda self: ()})()
    return type("Kernel", (), {"get_llm_registry": lambda self: registry})()


def _loader(started: list[bool]) -> object:
    return type("Loader", (), {"start": lambda self: started.append(True)})()
