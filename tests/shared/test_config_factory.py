from tusk.shared.config import ConfigFactory


def test_config_reads_conversation_agent_llm(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("CONVERSATION_AGENT_LLM", "groq/my-model")
    assert ConfigFactory().build().conversation_agent_llm.model == "my-model"


def test_config_reads_command_agent_llm(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("COMMAND_AGENT_LLM", "groq/command-model")
    assert ConfigFactory().build().command_agent_llm.model == "command-model"


def test_config_falls_back_to_agent_llm_for_command_agent(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_LLM", "groq/fallback-model")
    monkeypatch.delenv("COMMAND_AGENT_LLM", raising=False)
    assert ConfigFactory().build().command_agent_llm.model == "fallback-model"


def test_config_reads_stop_gate_llm(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("STOP_GATE_LLM", "groq/stop-model")
    assert ConfigFactory().build().stop_gate_llm.model == "stop-model"


def test_config_defaults_stop_gate_llm_to_llama_70b(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("STOP_GATE_LLM", raising=False)
    assert ConfigFactory().build().stop_gate_llm.model == "llama-3.3-70b-versatile"


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


def test_config_defaults_stt_engine_to_groq(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("STT_ENGINE", raising=False)
    assert ConfigFactory().build().stt_engine == "groq"


def test_config_reads_stt_engine(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("STT_ENGINE", "Whisper")
    assert ConfigFactory().build().stt_engine == "whisper"


def test_tts_enabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assert ConfigFactory().build().tts_enabled is True


def test_tts_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TUSK_TTS", "off")
    assert ConfigFactory().build().tts_enabled is False


def test_tts_speed_defaults_to_normal_and_reads_an_override(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assert ConfigFactory().build().tts_speed == 1.0
    monkeypatch.setenv("TUSK_TTS_SPEED", "1.5")
    assert ConfigFactory().build().tts_speed == 1.5


def test_ack_enabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("TUSK_ACK", raising=False)
    assert ConfigFactory().build().ack_enabled is True


def test_ack_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TUSK_ACK", "off")
    assert ConfigFactory().build().ack_enabled is False


def test_config_defaults_tray_icon_theme_and_activity(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("TUSK_TRAY_ICON_THEME", raising=False)
    monkeypatch.delenv("TUSK_TRAY_SHOW_LAST_ACTIVITY", raising=False)
    config = ConfigFactory().build()
    assert config.tray_icon_theme == "light" and config.tray_show_last_activity is False


def test_config_reads_tray_overrides(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TUSK_TRAY_ICON_THEME", "dark")
    monkeypatch.setenv("TUSK_TRAY_SHOW_LAST_ACTIVITY", "true")
    config = ConfigFactory().build()
    assert config.tray_icon_theme == "dark" and config.tray_show_last_activity is True
