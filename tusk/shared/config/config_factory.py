import os
import shlex

from tusk.shared.config.config import Config
from tusk.shared.schemas.llm_slot_config import LLMSlotConfig

__all__ = ["ConfigFactory"]


class ConfigFactory:
    def build(self) -> Config:
        return Config(
            **self._api_keys(), **self._llm_slots(), **self._audio(), **self._speech(),
            **self._timeouts(), **self._runtime(), **self._agent_backend(), **self._codex_exec(),
        )

    def _api_keys(self) -> dict:
        return {
            "groq_api_key": os.environ["GROQ_API_KEY"],
            "openrouter_api_key": os.environ.get("OPENROUTER_API_KEY", ""),
        }

    def _llm_slots(self) -> dict:
        return {
            "gatekeeper_llm": self._slot("GATEKEEPER_LLM", "groq/llama-3.1-8b-instant"),
            "stop_gate_llm": self._slot("STOP_GATE_LLM", "groq/llama-3.3-70b-versatile"),
            "conversation_agent_llm": self._agent_slot("CONVERSATION_AGENT_LLM"),
            "command_agent_llm": self._agent_slot("COMMAND_AGENT_LLM"),
            "planner_agent_llm": self._slot("PLANNER_AGENT_LLM", os.environ.get("PLANNER_LLM", "groq/openai/gpt-oss-20b")),
            "executor_agent_llm": self._agent_slot("EXECUTOR_AGENT_LLM"),
            "default_agent_llm": self._agent_slot("DEFAULT_AGENT_LLM"),
            "utility_llm": self._slot("UTILITY_LLM", "groq/llama-3.3-70b-versatile"),
        }

    def _audio(self) -> dict:
        return {
            "stt_engine": os.environ.get("STT_ENGINE", "groq").strip().lower(),
            "whisper_model_size": os.environ.get("WHISPER_MODEL_SIZE", "base"),
            # Whisper echoed the app list on silence and it did not fix app-name spelling, so it is opt-in.
            "stt_app_vocabulary": self._switch("STT_APP_VOCABULARY", "off"),
            "audio_sample_rate": self._int("AUDIO_SAMPLE_RATE", "16000"),
            "audio_frame_duration_ms": self._int("AUDIO_FRAME_DURATION_MS", "30"),
            "vad_aggressiveness": self._int("VAD_AGGRESSIVENESS", "2"),
            "vad_silence_ms": self._int("VAD_SILENCE_MS", "400"),
        }

    def _speech(self) -> dict:
        return {
            "tts_enabled": self._switch("TUSK_TTS", "on"),
            "tts_url": os.environ.get("TUSK_TTS_URL", ""),
            "tts_model": os.environ.get("TUSK_TTS_MODEL", "kokoro"),
            "tts_voice": os.environ.get("TUSK_TTS_VOICE", "am_michael"),
            "ack_enabled": self._switch("TUSK_ACK", "on"),
        }

    def _timeouts(self) -> dict:
        return {
            "follow_up_timeout_seconds": self._float("FOLLOW_UP_TIMEOUT_SECONDS", "30"),
            "max_follow_up_timeout_seconds": self._float("MAX_FOLLOW_UP_TIMEOUT_SECONDS", "120"),
            "gate_recovery_window_seconds": self._float("GATE_RECOVERY_WINDOW_SECONDS", "60"),
            "gate_recovery_candidate_limit": self._int("GATE_RECOVERY_CANDIDATE_LIMIT", "6"),
        }

    def _runtime(self) -> dict:
        shells = os.environ.get("TUSK_SHELLS", "voice")
        return {
            "shells": [item.strip() for item in shells.split(",") if item.strip()],
            "adapter_env_cache_dir": os.environ.get("TUSK_ADAPTER_ENV_CACHE_DIR", ".tusk_runtime/adapters"),
            "agent_session_log_dir": os.environ.get("TUSK_AGENT_SESSION_LOG_DIR", ".tusk_runtime/agent_sessions"),
            "tray_icon_theme": os.environ.get("TUSK_TRAY_ICON_THEME", "light"),
            "tray_show_last_activity": self._bool("TUSK_TRAY_SHOW_LAST_ACTIVITY", "false"),
        }

    def _agent_backend(self) -> dict:
        return {
            "agent_backend": os.environ.get("AGENT_BACKEND", "tusk"),
            "agent_backend_fallback": os.environ.get("AGENT_BACKEND_FALLBACK", ""),
        }

    def _codex_exec(self) -> dict:
        return {
            "codex_exec_binary": os.environ.get("CODEX_EXEC_BINARY", "codex"),
            "codex_exec_model": os.environ.get("CODEX_EXEC_MODEL", ""),
            "codex_exec_timeout_seconds": self._int("CODEX_EXEC_TIMEOUT_SECONDS", "60"),
            "codex_exec_workdir": os.environ.get("CODEX_EXEC_WORKDIR", ""),
            "codex_exec_sandbox_mode": os.environ.get("CODEX_EXEC_SANDBOX_MODE", "read-only"),
            "codex_exec_extra_args": tuple(shlex.split(os.environ.get("CODEX_EXEC_EXTRA_ARGS", ""))),
            "codex_exec_output_schema_path": os.environ.get("CODEX_EXEC_OUTPUT_SCHEMA_PATH", self._schema_path()),
            "codex_exec_log_raw_events": self._bool("CODEX_EXEC_LOG_RAW_EVENTS", "false"),
        }

    def _slot(self, name: str, default: str) -> LLMSlotConfig:
        return LLMSlotConfig.parse(os.environ.get(name, default))

    def _agent_slot(self, name: str) -> LLMSlotConfig:
        return self._slot(name, os.environ.get("AGENT_LLM", "groq/openai/gpt-oss-120b"))

    def _int(self, name: str, default: str) -> int:
        return int(os.environ.get(name, default))

    def _float(self, name: str, default: str) -> float:
        return float(os.environ.get(name, default))

    def _bool(self, name: str, default: str) -> bool:
        return os.environ.get(name, default).strip().lower() in ("true", "1", "yes", "on")

    def _switch(self, name: str, default: str) -> bool:
        # Opposite polarity to _bool: on unless explicitly turned off (documented in docs/specification.md).
        return os.environ.get(name, default).lower() not in ("off", "0", "false")

    def _schema_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "kernel", "agent", "backends", "codex_agent_result.schema.json")
