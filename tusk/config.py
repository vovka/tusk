import os
from dataclasses import dataclass

__all__ = ["Config"]


@dataclass(frozen=True)
class Config:
    openrouter_api_key: str
    groq_api_key: str
    gatekeeper_model: str
    main_agent_model: str
    whisper_model_size: str
    audio_sample_rate: int
    audio_frame_duration_ms: int
    vad_aggressiveness: int

    @staticmethod
    def from_env() -> "Config":
        return Config(
            openrouter_api_key=os.environ["OPENROUTER_API_KEY"],
            groq_api_key=os.environ.get("GROQ_API_KEY", ""),
            gatekeeper_model=os.environ.get("GATEKEEPER_MODEL", "liquid/lfm-2-24b-a2b"),
            main_agent_model=os.environ.get("MAIN_AGENT_MODEL", "x-ai/grok-4.1-fast"),
            whisper_model_size=os.environ.get("WHISPER_MODEL_SIZE", "base"),
            audio_sample_rate=int(os.environ.get("AUDIO_SAMPLE_RATE", "16000")),
            audio_frame_duration_ms=int(os.environ.get("AUDIO_FRAME_DURATION_MS", "30")),
            vad_aggressiveness=int(os.environ.get("VAD_AGGRESSIVENESS", "2")),
        )
