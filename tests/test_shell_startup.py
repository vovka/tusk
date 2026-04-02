import types

import main


def test_main_starts_requested_shells(monkeypatch) -> None:
    config = types.SimpleNamespace(shells=["cli"], adapter_env_cache_dir=".tusk_runtime/adapters")
    log = types.SimpleNamespace(log=lambda *a: None)
    shell = types.SimpleNamespace(start=lambda submit: setattr(shell, "submit", submit))
    monkeypatch.setattr(main.StartupOptions, "from_sources", lambda argv=None: types.SimpleNamespace(log_groups=frozenset()))
    monkeypatch.setattr(main.Config, "from_env", lambda: config)
    monkeypatch.setattr(main, "_build_log", lambda options: log)
    monkeypatch.setattr(main, "_build_kernel", lambda c, l: types.SimpleNamespace(submit=lambda text: None))
    monkeypatch.setattr(main, "_load_shells", lambda c, kernel, logger: [shell])
    main.main()
    assert hasattr(shell, "submit")


def test_main_logs_ready_message(monkeypatch) -> None:
    logs: list[tuple[str, str, str]] = []
    _stub_main(monkeypatch, types.SimpleNamespace(log=lambda *args: logs.append(args)))
    main.main()
    assert ("READY", "TUSK is ready.", "startup") in logs


def _stub_main(monkeypatch, log: object) -> None:
    config = types.SimpleNamespace(shells=["cli"], adapter_env_cache_dir=".tusk_runtime/adapters")
    shell = types.SimpleNamespace(start=lambda submit: None)
    monkeypatch.setattr(main.StartupOptions, "from_sources", lambda argv=None: types.SimpleNamespace(log_groups=frozenset()))
    monkeypatch.setattr(main.Config, "from_env", lambda: config)
    monkeypatch.setattr(main, "_build_log", lambda options: log)
    monkeypatch.setattr(main, "_build_kernel", lambda c, l: types.SimpleNamespace(submit=lambda text: None))
    monkeypatch.setattr(main, "_load_shells", lambda c, kernel, logger: [shell])
