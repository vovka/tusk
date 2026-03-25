import os
from dataclasses import dataclass

from tusk.kernel.schemas.llm_slot_config import LLMSlotConfig

__all__ = ["Config"]


@dataclass(frozen=True)
class Config:
    groq_api_key: str
    openrouter_api_key: str
    gatekeeper_llm: LLMSlotConfig
    agent_llm: LLMSlotConfig
    utility_llm: LLMSlotConfig
    whisper_model_size: str
    audio_sample_rate: int
    audio_frame_duration_ms: int
    vad_aggressiveness: int
    follow_up_timeout_seconds: float
    shells: list[str]
    adapter_env_cache_dir: str

    @staticmethod
    def from_env() -> "Config":
        shells = os.environ.get("TUSK_SHELLS", "voice")
        return Config(
            groq_api_key=os.environ["GROQ_API_KEY"],
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            gatekeeper_llm=LLMSlotConfig.parse(os.environ.get("GATEKEEPER_LLM", "groq/llama-3.1-8b-instant")),
            agent_llm=LLMSlotConfig.parse(os.environ.get("AGENT_LLM", "groq/openai/gpt-oss-120b")),
            utility_llm=LLMSlotConfig.parse(os.environ.get("UTILITY_LLM", "groq/llama-3.3-70b-versatile")),
            whisper_model_size=os.environ.get("WHISPER_MODEL_SIZE", "base"),
            audio_sample_rate=int(os.environ.get("AUDIO_SAMPLE_RATE", "16000")),
            audio_frame_duration_ms=int(os.environ.get("AUDIO_FRAME_DURATION_MS", "30")),
            vad_aggressiveness=int(os.environ.get("VAD_AGGRESSIVENESS", "2")),
            follow_up_timeout_seconds=float(os.environ.get("FOLLOW_UP_TIMEOUT_SECONDS", "30")),
            shells=[item.strip() for item in shells.split(",") if item.strip()],
            adapter_env_cache_dir=os.environ.get("TUSK_ADAPTER_ENV_CACHE_DIR", ".tusk_runtime/adapters"),
        )
