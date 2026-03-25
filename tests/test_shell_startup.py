import types

import main


def test_main_starts_requested_shells(monkeypatch) -> None:
    config = types.SimpleNamespace(shells=["cli"], adapter_env_cache_dir=".tusk_runtime/adapters")
    log = types.SimpleNamespace(log=lambda *a: None)
    shell = types.SimpleNamespace(start=lambda api: setattr(shell, "api", api))
    monkeypatch.setattr(main.Config, "from_env", lambda: config)
    monkeypatch.setattr(main, "_build_log", lambda: log)
    monkeypatch.setattr(main, "_build_kernel", lambda c, l: types.SimpleNamespace())
    monkeypatch.setattr(main, "_load_shells", lambda c, api: [shell])
    main.main()
    assert hasattr(shell, "api")

