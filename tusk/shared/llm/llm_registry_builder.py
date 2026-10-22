from tusk.shared.config.config import Config
from tusk.shared.config.startup_options import StartupOptions
from tusk.shared.interrupt.interrupt_token import InterruptToken
from tusk.shared.llm.interfaces.llm_provider import LLMProvider
from tusk.shared.llm.interfaces.llm_provider_factory import LLMProviderFactory
from tusk.shared.llm.llm_proxy import LLMProxy
from tusk.shared.llm.llm_registry import LLMRegistry
from tusk.shared.llm.rotating_llm_provider import RotatingLLMProvider
from tusk.shared.logging.interfaces.log_printer import LogPrinter
from tusk.shared.schemas.llm_slot_config import LLMSlotConfig
from tusk.shared.tracing.interfaces.tracer import Tracer

__all__ = ["LLMRegistryBuilder"]

# (slot name, Config attribute, needs interrupt token); the gatekeeper/stop_gate/utility
# slots get no token: they must stay usable while an interrupt is pending
_SLOTS: tuple[tuple[str, str, bool], ...] = (
    ("gatekeeper", "gatekeeper_llm", False),
    ("stop_gate", "stop_gate_llm", False),
    ("conversation_agent", "conversation_agent_llm", True),
    ("command_agent", "command_agent_llm", True),
    ("planner_agent", "planner_agent_llm", True),
    ("executor_agent", "executor_agent_llm", True),
    ("default_agent", "default_agent_llm", True),
    ("utility", "utility_llm", False),
)


class LLMRegistryBuilder:
    def __init__(self, factory: LLMProviderFactory, config: Config, log: LogPrinter, options: StartupOptions, interrupt_token: InterruptToken, tracer: Tracer) -> None:
        self._factory = factory
        self._config = config
        self._log = log
        self._options = options
        self._interrupt_token = interrupt_token
        self._tracer = tracer

    def build(self) -> LLMRegistry:
        registry = LLMRegistry(self._factory)
        for slot_name, config_attribute, needs_interrupt_token in _SLOTS:
            slot = getattr(self._config, config_attribute)
            registry.register_slot(slot_name, self._proxy(slot_name, slot, needs_interrupt_token))
        return registry

    def _proxy(self, slot_name: str, slot: LLMSlotConfig, needs_interrupt_token: bool) -> LLMProxy:
        token = self._interrupt_token if needs_interrupt_token else None
        return LLMProxy(
            self._provider(slot_name, slot), self._log, slot_name, enabled_log_groups=self._options.log_groups,
            preview_chars=self._options.llm_log_preview_chars, interrupt_token=token, tracer=self._tracer,
        )

    def _provider(self, slot_name: str, slot: LLMSlotConfig) -> LLMProvider:
        if not slot.rotation:
            return self._factory.create(slot.provider_name, slot.model)
        providers = [self._factory.create(*item.split("/", 1)) for item in slot.rotation]
        return RotatingLLMProvider(providers, lambda exc, label: self._log_failover(slot_name, exc, label))

    def _log_failover(self, slot_name: str, exc: Exception, label: str) -> None:
        self._log.log("LLMREQUEST", f"[{slot_name}] 429, failing over to {label}: {exc}", "llm-request")
