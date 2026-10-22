from tusk.shared.interfaces.llm_provider import LLMProvider
from tusk.shared.interfaces.llm_provider_factory import LLMProviderFactory
from tusk.shared.llm.llm_proxy import LLMProxy

__all__ = ["LLMRegistry"]


class LLMRegistry:
    def __init__(self, factory: LLMProviderFactory) -> None:
        self._factory = factory
        self._slots: dict[str, LLMProxy] = {}

    def register_slot(self, name: str, proxy: LLMProxy) -> None:
        self._slots[name] = proxy

    def get(self, name: str) -> LLMProvider:
        return self._slots[name]

    def get_with_fallback(self, name: str, fallback_name: str) -> LLMProvider:
        if name in self._slots:
            return self._slots[name]
        return self._slots[fallback_name]

    def swap(self, slot_name: str, provider_name: str, model: str) -> str:
        new_provider = self._factory.create(provider_name, model)
        self._verify(new_provider, f"{provider_name}/{model}")
        self._slots[slot_name].swap(new_provider)
        return f"{slot_name} -> {provider_name}/{model}"

    def _verify(self, provider: LLMProvider, label: str) -> None:
        # a typo'd model id would otherwise only fail on the slot's next real call
        try:
            getattr(provider, "verify", lambda: None)()
        except Exception as exc:
            known = ", ".join(sorted({proxy.label for proxy in self._slots.values()}))
            raise ValueError(f"unknown model {label}; known: {known}") from exc

    @property
    def slot_names(self) -> list[str]:
        return list(self._slots.keys())

    def model_labels(self) -> tuple[tuple[str, str], ...]:
        return tuple((name, proxy.label) for name, proxy in self._slots.items())
