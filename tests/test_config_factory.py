from tusk.shared.config import Config, ConfigFactory

CODEX_ENV_NAMES = "AGENT_BACKEND CODEX_EXEC_BINARY CODEX_EXEC_MODEL CODEX_EXEC_TIMEOUT_SECONDS CODEX_EXEC_WORKDIR CODEX_EXEC_SANDBOX_MODE CODEX_EXEC_EXTRA_ARGS CODEX_EXEC_OUTPUT_SCHEMA_PATH CODEX_EXEC_LOG_RAW_EVENTS".split()


CODEX_CONFIG_NAMES = "agent_backend codex_exec_binary codex_exec_model codex_exec_timeout_seconds codex_exec_workdir codex_exec_sandbox_mode codex_exec_extra_args codex_exec_output_schema_path codex_exec_log_raw_events".split()


def codex_values(config: Config) -> dict:
    return {name: getattr(config, name) for name in CODEX_CONFIG_NAMES}


def set_codex_env(monkeypatch) -> None:
    values = {
        "AGENT_BACKEND": "codex", "CODEX_EXEC_BINARY": "/usr/local/bin/codex",
        "CODEX_EXEC_MODEL": "gpt-5.5", "CODEX_EXEC_TIMEOUT_SECONDS": "120",
        "CODEX_EXEC_WORKDIR": "/workspace/project", "CODEX_EXEC_SANDBOX_MODE": "workspace-write",
        "CODEX_EXEC_EXTRA_ARGS": "--json --message \"hello world\" --tags=key1=val1,key2=val2",
        "CODEX_EXEC_OUTPUT_SCHEMA_PATH": "/tmp/schema.json", "CODEX_EXEC_LOG_RAW_EVENTS": "yes",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_config_reads_conversation_agent_llm(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("CONVERSATION_AGENT_LLM", "groq/my-model")
    assert ConfigFactory().build().conversation_agent_llm.model == "my-model"


def test_config_reads_planner_agent_llm(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("PLANNER_AGENT_LLM", "groq/openai/gpt-oss-20b")
    assert ConfigFactory().build().planner_agent_llm.model == "openai/gpt-oss-20b"


def test_config_reads_executor_agent_llm(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("EXECUTOR_AGENT_LLM", "groq/exec-model")
    assert ConfigFactory().build().executor_agent_llm.model == "exec-model"


def test_config_reads_default_agent_llm(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("DEFAULT_AGENT_LLM", "groq/default-model")
    assert ConfigFactory().build().default_agent_llm.model == "default-model"


def test_config_falls_back_to_agent_llm_for_conversation(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_LLM", "groq/fallback-model")
    monkeypatch.delenv("CONVERSATION_AGENT_LLM", raising=False)
    assert ConfigFactory().build().conversation_agent_llm.model == "fallback-model"


def test_config_falls_back_to_planner_llm_for_planner_agent(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("PLANNER_LLM", "groq/openai/gpt-oss-20b")
    monkeypatch.delenv("PLANNER_AGENT_LLM", raising=False)
    assert ConfigFactory().build().planner_agent_llm.model == "openai/gpt-oss-20b"


def test_config_reads_agent_session_log_dir(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TUSK_AGENT_SESSION_LOG_DIR", "/tmp/sessions")
    assert ConfigFactory().build().agent_session_log_dir == "/tmp/sessions"


def test_config_defaults_agent_session_log_dir(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("TUSK_AGENT_SESSION_LOG_DIR", raising=False)
    assert ConfigFactory().build().agent_session_log_dir == ".tusk_runtime/agent_sessions"


def test_config_reads_gate_recovery_window(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GATE_RECOVERY_WINDOW_SECONDS", "45")
    assert ConfigFactory().build().gate_recovery_window_seconds == 45.0


def test_config_defaults_gate_recovery_candidate_limit(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("GATE_RECOVERY_CANDIDATE_LIMIT", raising=False)
    assert ConfigFactory().build().gate_recovery_candidate_limit == 6


def test_tts_enabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assert ConfigFactory().build().tts_enabled is True


def test_tts_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TUSK_TTS", "off")
    assert ConfigFactory().build().tts_enabled is False


def test_config_defaults_codex_exec_values(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    for name in CODEX_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    assert codex_values(ConfigFactory().build()) == {
        "agent_backend": "tusk", "codex_exec_binary": "codex", "codex_exec_model": "",
        "codex_exec_timeout_seconds": 60, "codex_exec_workdir": "", "codex_exec_sandbox_mode": "read-only",
        "codex_exec_extra_args": (), "codex_exec_output_schema_path": ConfigFactory()._schema_path(),
        "codex_exec_log_raw_events": False,
    }


def test_config_reads_codex_exec_values(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    set_codex_env(monkeypatch)
    assert codex_values(ConfigFactory().build()) == {
        "agent_backend": "codex", "codex_exec_binary": "/usr/local/bin/codex", "codex_exec_model": "gpt-5.5",
        "codex_exec_timeout_seconds": 120, "codex_exec_workdir": "/workspace/project",
        "codex_exec_sandbox_mode": "workspace-write",
        "codex_exec_extra_args": ("--json", "--message", "hello world", "--tags=key1=val1,key2=val2"),
        "codex_exec_output_schema_path": "/tmp/schema.json", "codex_exec_log_raw_events": True,
    }
