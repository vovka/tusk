import os

from tusk.shared.config.config import Config
from tusk.shared.schemas.llm_slot_config import LLMSlotConfig

__all__ = ["ConfigFactory"]


class ConfigFactory:
    def build(self) -> Config:
        shells = os.environ.get("TUSK_SHELLS", "voice")
        values = self._base_values(shells)
        return Config(**values)

    def _slot(self, name: str, default: str) -> LLMSlotConfig:
        return LLMSlotConfig.parse(os.environ.get(name, default))

    def _int(self, name: str, default: str) -> int:
        return int(os.environ.get(name, default))

    def _float(self, name: str, default: str) -> float:
        return float(os.environ.get(name, default))

    def _shells(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    def _base_values(self, shells: str) -> dict:
        return {**self._llm_values(), **self._runtime_values(shells)}

    def _llm_values(self) -> dict:
        return {**self._api_keys(), **self._agent_llm_slots()}

    def _api_keys(self) -> dict:
        return {
            "groq_api_key": os.environ["GROQ_API_KEY"],
            "openrouter_api_key": os.environ.get("OPENROUTER_API_KEY", ""),
        }

    def _agent_llm_slots(self) -> dict:
        agent = os.environ.get("AGENT_LLM", "groq/openai/gpt-oss-120b")
        planner = os.environ.get("PLANNER_LLM", "groq/openai/gpt-oss-20b")
        return {
            "gatekeeper_llm": self._slot("GATEKEEPER_LLM", "groq/llama-3.1-8b-instant"),
            "conversation_agent_llm": self._slot("CONVERSATION_AGENT_LLM", agent),
            "planner_agent_llm": self._slot("PLANNER_AGENT_LLM", planner),
            "executor_agent_llm": self._slot("EXECUTOR_AGENT_LLM", agent),
            "default_agent_llm": self._slot("DEFAULT_AGENT_LLM", agent),
            "utility_llm": self._slot("UTILITY_LLM", "groq/llama-3.3-70b-versatile"),
        }

    def _runtime_values(self, shells: str) -> dict:
        return {**self._audio_values(), **self._environment_values(shells)}

    def _audio_values(self) -> dict:
        return {
            "whisper_model_size": os.environ.get("WHISPER_MODEL_SIZE", "base"),
            "audio_sample_rate": self._int("AUDIO_SAMPLE_RATE", "16000"),
            "audio_frame_duration_ms": self._int("AUDIO_FRAME_DURATION_MS", "30"),
            "vad_aggressiveness": self._int("VAD_AGGRESSIVENESS", "2"),
        }

    def _environment_values(self, shells: str) -> dict:
        return {
            "follow_up_timeout_seconds": self._float("FOLLOW_UP_TIMEOUT_SECONDS", "30"),
            "max_follow_up_timeout_seconds": self._float("MAX_FOLLOW_UP_TIMEOUT_SECONDS", "120"),
            "gate_recovery_window_seconds": self._float("GATE_RECOVERY_WINDOW_SECONDS", "60"),
            "gate_recovery_candidate_limit": self._int("GATE_RECOVERY_CANDIDATE_LIMIT", "6"),
            "shells": self._shells(shells),
            "adapter_env_cache_dir": os.environ.get("TUSK_ADAPTER_ENV_CACHE_DIR", ".tusk_runtime/adapters"),
            "conversation_log_dir": os.environ.get("TUSK_CONVERSATION_LOG_DIR", ".tusk_runtime/conversations"),
            "agent_session_log_dir": os.environ.get("TUSK_AGENT_SESSION_LOG_DIR", ".tusk_runtime/agent_sessions"),
        }
