
from tusk.shared.config import ConfigFactory
from tusk.shared.schemas.llm_slot_config import LLMSlotConfig

ENV_NAMES = """
    OPENROUTER_API_KEY AGENT_LLM PLANNER_LLM GATEKEEPER_LLM STOP_GATE_LLM CONVERSATION_AGENT_LLM
    COMMAND_AGENT_LLM PLANNER_AGENT_LLM EXECUTOR_AGENT_LLM DEFAULT_AGENT_LLM UTILITY_LLM
    STT_ENGINE WHISPER_MODEL_SIZE STT_APP_VOCABULARY AUDIO_SAMPLE_RATE AUDIO_FRAME_DURATION_MS
    VAD_AGGRESSIVENESS VAD_SILENCE_MS TUSK_TTS TUSK_TTS_URL TUSK_TTS_MODEL TUSK_TTS_VOICE TUSK_ACK
    FOLLOW_UP_TIMEOUT_SECONDS MAX_FOLLOW_UP_TIMEOUT_SECONDS GATE_RECOVERY_WINDOW_SECONDS
    GATE_RECOVERY_CANDIDATE_LIMIT TUSK_SHELLS TUSK_ADAPTER_ENV_CACHE_DIR TUSK_AGENT_SESSION_LOG_DIR
    TUSK_TRAY_ICON_THEME TUSK_TRAY_SHOW_LAST_ACTIVITY AGENT_BACKEND AGENT_BACKEND_FALLBACK
    CODEX_EXEC_BINARY CODEX_EXEC_MODEL CODEX_EXEC_TIMEOUT_SECONDS CODEX_EXEC_WORKDIR
    CODEX_EXEC_SANDBOX_MODE CODEX_EXEC_EXTRA_ARGS CODEX_EXEC_OUTPUT_SCHEMA_PATH CODEX_EXEC_LOG_RAW_EVENTS
""".split()

AGENT_LLM = LLMSlotConfig.parse("groq/openai/gpt-oss-120b")

EXPECTED_DEFAULTS = {
    "groq_api_key": "test-key",
    "openrouter_api_key": "",
    "gatekeeper_llm": LLMSlotConfig.parse("groq/llama-3.1-8b-instant"),
    "stop_gate_llm": LLMSlotConfig.parse("groq/llama-3.3-70b-versatile"),
    "conversation_agent_llm": AGENT_LLM,
    "command_agent_llm": AGENT_LLM,
    "planner_agent_llm": LLMSlotConfig.parse("groq/openai/gpt-oss-20b"),
    "executor_agent_llm": AGENT_LLM,
    "default_agent_llm": AGENT_LLM,
    "utility_llm": LLMSlotConfig.parse("groq/llama-3.3-70b-versatile"),
    "stt_engine": "groq",
    "whisper_model_size": "base",
    "stt_app_vocabulary": False,
    "audio_sample_rate": 16000,
    "audio_frame_duration_ms": 30,
    "vad_aggressiveness": 2,
    "vad_silence_ms": 400,
    "tts_enabled": True,
    "tts_url": "",
    "tts_model": "kokoro",
    "tts_voice": "am_michael",
    "ack_enabled": True,
    "follow_up_timeout_seconds": 30.0,
    "max_follow_up_timeout_seconds": 120.0,
    "gate_recovery_window_seconds": 60.0,
    "gate_recovery_candidate_limit": 6,
    "shells": ["voice"],
    "adapter_env_cache_dir": ".tusk_runtime/adapters",
    "agent_session_log_dir": ".tusk_runtime/agent_sessions",
    "tray_icon_theme": "light",
    "tray_show_last_activity": False,
    "agent_backend": "tusk",
    "agent_backend_fallback": "",
    "codex_exec_binary": "codex",
    "codex_exec_model": "",
    "codex_exec_timeout_seconds": 60,
    "codex_exec_workdir": "",
    "codex_exec_sandbox_mode": "read-only",
    "codex_exec_extra_args": (),
    "codex_exec_log_raw_events": False,
}


def test_every_config_default_is_pinned(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    actual = dict(vars(ConfigFactory().build()))
    schema_path = actual.pop("codex_exec_output_schema_path")
    assert actual == EXPECTED_DEFAULTS
    assert schema_path.endswith("tusk/kernel/agent/backends/codex_agent_result.schema.json")


def test_switch_booleans_are_on_unless_turned_off(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TUSK_TTS", "0")
    monkeypatch.setenv("TUSK_ACK", "FALSE")
    config = ConfigFactory().build()
    assert (config.tts_enabled, config.ack_enabled) == (False, False)


def test_flag_booleans_are_off_unless_turned_on(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TUSK_TRAY_SHOW_LAST_ACTIVITY", "maybe")
    monkeypatch.setenv("CODEX_EXEC_LOG_RAW_EVENTS", " YES ")
    config = ConfigFactory().build()
    assert (config.tray_show_last_activity, config.codex_exec_log_raw_events) == (False, True)
