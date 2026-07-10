import json
from pathlib import Path

from tusk.shared.config import Config, ConfigFactory

CODEX_ENV_NAMES = "AGENT_BACKEND AGENT_BACKEND_FALLBACK CODEX_EXEC_BINARY CODEX_EXEC_MODEL CODEX_EXEC_TIMEOUT_SECONDS CODEX_EXEC_WORKDIR CODEX_EXEC_SANDBOX_MODE CODEX_EXEC_EXTRA_ARGS CODEX_EXEC_OUTPUT_SCHEMA_PATH CODEX_EXEC_LOG_RAW_EVENTS".split()


CODEX_CONFIG_NAMES = "agent_backend agent_backend_fallback codex_exec_binary codex_exec_model codex_exec_timeout_seconds codex_exec_workdir codex_exec_sandbox_mode codex_exec_extra_args codex_exec_output_schema_path codex_exec_log_raw_events".split()


def codex_values(config: Config) -> dict:
    return {name: getattr(config, name) for name in CODEX_CONFIG_NAMES}


def set_codex_env(monkeypatch) -> None:
    values = {
        "AGENT_BACKEND": "codex", "AGENT_BACKEND_FALLBACK": "tusk", "CODEX_EXEC_BINARY": "/usr/local/bin/codex",
        "CODEX_EXEC_MODEL": "gpt-5.5", "CODEX_EXEC_TIMEOUT_SECONDS": "120",
        "CODEX_EXEC_WORKDIR": "/workspace/project", "CODEX_EXEC_SANDBOX_MODE": "workspace-write",
        "CODEX_EXEC_EXTRA_ARGS": "--json --message \"hello world\" --tags=key1=val1,key2=val2",
        "CODEX_EXEC_OUTPUT_SCHEMA_PATH": "/tmp/schema.json", "CODEX_EXEC_LOG_RAW_EVENTS": "yes",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_config_defaults_codex_exec_values(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    for name in CODEX_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    assert codex_values(ConfigFactory().build()) == {
        "agent_backend": "tusk", "agent_backend_fallback": "", "codex_exec_binary": "codex", "codex_exec_model": "",
        "codex_exec_timeout_seconds": 60, "codex_exec_workdir": "", "codex_exec_sandbox_mode": "read-only",
        "codex_exec_extra_args": (), "codex_exec_output_schema_path": ConfigFactory()._schema_path(),
        "codex_exec_log_raw_events": False,
    }


def test_config_reads_codex_exec_values(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    set_codex_env(monkeypatch)
    assert codex_values(ConfigFactory().build()) == {
        "agent_backend": "codex", "agent_backend_fallback": "tusk", "codex_exec_binary": "/usr/local/bin/codex", "codex_exec_model": "gpt-5.5",
        "codex_exec_timeout_seconds": 120, "codex_exec_workdir": "/workspace/project",
        "codex_exec_sandbox_mode": "workspace-write",
        "codex_exec_extra_args": ("--json", "--message", "hello world", "--tags=key1=val1,key2=val2"),
        "codex_exec_output_schema_path": "/tmp/schema.json", "codex_exec_log_raw_events": True,
    }


def test_config_default_codex_exec_schema_path_exists(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("CODEX_EXEC_OUTPUT_SCHEMA_PATH", raising=False)
    path = ConfigFactory().build().codex_exec_output_schema_path
    assert Path(path).exists()


def test_config_default_codex_exec_schema_is_openai_strict_compliant(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    path = ConfigFactory().build().codex_exec_output_schema_path
    schema = json.loads(Path(path).read_text())
    properties = schema["properties"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(properties)
    assert {"status", "reply", "final_text"} <= set(properties)
