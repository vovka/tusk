from dataclasses import dataclass

__all__ = ["LLMSlotConfig"]


@dataclass(frozen=True)
class LLMSlotConfig:
    provider_name: str
    model: str

    @staticmethod
    def parse(value: str) -> "LLMSlotConfig":
        provider, _, model = value.partition("/")
        return LLMSlotConfig(provider_name=provider, model=model)
