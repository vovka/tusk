import types

import launcher.tusk_host_launcher as launcher
import main


def test_launcher_main_and_serve(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(launcher, "_SOCKET_PATH", str(tmp_path / "sock"))
    monkeypatch.setattr("os.path.exists", lambda p: False)
    monkeypatch.setattr("os.makedirs", lambda *a, **k: None)
    monkeypatch.setattr("os.chmod", lambda *a, **k: None)
    monkeypatch.setattr(launcher, "_serve", lambda sock: None)
    class Sock:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def bind(self, path): self.path = path
        def listen(self, n): self.n = n
    monkeypatch.setattr("socket.socket", lambda *a: Sock())
    launcher.main()


def test_main_entry(monkeypatch) -> None:
    cfg = types.SimpleNamespace()
    pipe = types.SimpleNamespace(run=lambda: setattr(pipe, "ran", True))
    monkeypatch.setattr(main.Config, "from_env", lambda: cfg)
    monkeypatch.setattr(main, "_build_pipeline", lambda c, l: pipe)
    main.main()
    assert pipe.ran


def test_build_pipeline_wires_components(monkeypatch) -> None:
    cfg = types.SimpleNamespace(groq_api_key="k", openrouter_api_key="o", gatekeeper_llm=types.SimpleNamespace(provider_name="groq", model="m"), agent_llm=types.SimpleNamespace(provider_name="groq", model="m"), utility_llm=types.SimpleNamespace(provider_name="groq", model="m"), audio_sample_rate=1, audio_frame_duration_ms=1, vad_aggressiveness=1, follow_up_timeout_seconds=1, max_follow_up_timeout_seconds=120, conversation_log_directory="/tmp/tusk/conversations")
    monkeypatch.setattr(main, "_build_llm_registry", lambda c, l=None: types.SimpleNamespace(get=lambda n: types.SimpleNamespace(), slot_names=[]))
    monkeypatch.setattr(main, "build_tool_registry", lambda *a: types.SimpleNamespace(register=lambda t: None))
    monkeypatch.setattr(main, "Pipeline", lambda **k: types.SimpleNamespace())
    pipe = main._build_pipeline(cfg, types.SimpleNamespace(log=lambda *a: None))
    assert pipe is not None
