from dataclasses import dataclass

__all__ = ["LLMSlotConfig"]


@dataclass(frozen=True)
class LLMSlotConfig:
    provider_name: str
    model: str
    rotation: tuple[str, ...] = ()

    @staticmethod
    def parse(value: str) -> "LLMSlotConfig":
        # "a/x,b/y" rotates requests across models; the first one names the slot
        items = tuple(item.strip() for item in value.split(",") if item.strip())
        provider, _, model = items[0].partition("/") if items else ("", "", "")
        return LLMSlotConfig(provider_name=provider, model=model, rotation=items if len(items) > 1 else ())
