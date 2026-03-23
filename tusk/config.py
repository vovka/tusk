import os
from dataclasses import dataclass

__all__ = ["Config"]


@dataclass(frozen=True)
class Config:
    groq_api_key: str
    gatekeeper_model: str
    main_agent_model: str
    utility_model: str
    whisper_model_size: str
    audio_sample_rate: int
    audio_frame_duration_ms: int
    vad_aggressiveness: int
    openrouter_api_key: str

    @staticmethod
    def from_env() -> "Config":
        return Config(
            groq_api_key=os.environ["GROQ_API_KEY"],
            gatekeeper_model=os.environ.get("GATEKEEPER_MODEL", "llama-3.1-8b-instant"),
            main_agent_model=os.environ.get("MAIN_AGENT_MODEL", "openai/gpt-oss-120b"),
            utility_model=os.environ.get("UTILITY_MODEL", "llama-3.3-70b-versatile"),
            whisper_model_size=os.environ.get("WHISPER_MODEL_SIZE", "base"),
            audio_sample_rate=int(os.environ.get("AUDIO_SAMPLE_RATE", "16000")),
            audio_frame_duration_ms=int(os.environ.get("AUDIO_FRAME_DURATION_MS", "30")),
            vad_aggressiveness=int(os.environ.get("VAD_AGGRESSIVENESS", "2")),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )
