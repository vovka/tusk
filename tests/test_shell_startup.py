import types

import main


def test_main_builds_reporter_and_starts_loader(monkeypatch) -> None:
    captured: dict = {}
    _stub_main(monkeypatch, captured)
    main.main()
    assert captured["started"] and captured["reporter"] is captured["loader_reporter"]


def test_main_publishes_initial_model_labels(monkeypatch) -> None:
    captured: dict = {}
    _stub_main(monkeypatch, captured)
    main.main()
    assert captured["models"] == (("gatekeeper", "groq/llama"),)


def _stub_main(monkeypatch, captured: dict) -> None:
    config = types.SimpleNamespace(shells=["cli"])
    registry = types.SimpleNamespace(model_labels=lambda: (("gatekeeper", "groq/llama"),))
    kernel = types.SimpleNamespace(get_llm_registry=lambda: registry)
    monkeypatch.setattr(main.StartupOptions, "from_sources", lambda argv=None: types.SimpleNamespace())
    monkeypatch.setattr(main.Config, "from_env", lambda: config)
    monkeypatch.setattr(main, "_build_log", lambda options: types.SimpleNamespace(log=lambda *a: None))
    monkeypatch.setattr(main, "StatusReporterHub", lambda sink, logger: _reporter(captured))
    monkeypatch.setattr(main, "_build_kernel", lambda c, l, o, reporter: kernel)
    monkeypatch.setattr(main, "ShellLoader", lambda c, k, l, reporter: _loader(captured, reporter))


def _reporter(captured: dict) -> object:
    reporter = types.SimpleNamespace(set_models=lambda models: captured.__setitem__("models", models))
    captured["reporter"] = reporter
    return reporter


def _loader(captured: dict, reporter: object) -> object:
    captured["loader_reporter"] = reporter
    return types.SimpleNamespace(start=lambda: captured.__setitem__("started", True))
