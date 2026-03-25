from tusk.kernel.interfaces.llm_provider import LLMProvider
from tusk.kernel.interfaces.llm_provider_factory import LLMProviderFactory
from tusk.kernel.llm_proxy import LLMProxy

__all__ = ["LLMRegistry"]


class LLMRegistry:
    def __init__(self, factory: LLMProviderFactory) -> None:
        self._factory = factory
        self._slots: dict[str, LLMProxy] = {}

    def register_slot(self, name: str, proxy: LLMProxy) -> None:
        self._slots[name] = proxy

    def get(self, name: str) -> LLMProvider:
        return self._slots[name]

    def swap(self, slot_name: str, provider_name: str, model: str) -> str:
        new_provider = self._factory.create(provider_name, model)
        self._slots[slot_name].swap(new_provider)
        return f"{slot_name} -> {provider_name}/{model}"

    @property
    def slot_names(self) -> list[str]:
        return list(self._slots.keys())
