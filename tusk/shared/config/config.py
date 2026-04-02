from dataclasses import dataclass

from tusk.shared.schemas.llm_slot_config import LLMSlotConfig

__all__ = ["Config"]


@dataclass(frozen=True)
class Config:
    groq_api_key: str
    openrouter_api_key: str
    gatekeeper_llm: LLMSlotConfig
    conversation_agent_llm: LLMSlotConfig
    planner_agent_llm: LLMSlotConfig
    executor_agent_llm: LLMSlotConfig
    default_agent_llm: LLMSlotConfig
    utility_llm: LLMSlotConfig
    whisper_model_size: str
    audio_sample_rate: int
    audio_frame_duration_ms: int
    vad_aggressiveness: int
    follow_up_timeout_seconds: float
    max_follow_up_timeout_seconds: float
    gate_recovery_window_seconds: float
    gate_recovery_candidate_limit: int
    shells: list[str]
    adapter_env_cache_dir: str
    conversation_log_dir: str
    agent_session_log_dir: str

    @staticmethod
    def from_env() -> "Config":
        from tusk.shared.config.config_factory import ConfigFactory

        return ConfigFactory().build()
