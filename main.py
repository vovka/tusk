import sys

from shell_loader import ShellLoader
from tusk.kernel import KernelAPI
from tusk.kernel.core.startup import build_kernel
from tusk.providers.llm import ConfigurableLLMFactory
from tusk.shared.config import Config, StartupOptions
from tusk.shared.interrupt import InterruptToken
from tusk.shared.llm import LLMProxy, LLMRegistry
from tusk.shared.logging import ColorLogPrinter
from tusk.shared.status import NullStatusSink, StatusReporterHub


def _build_log(options: StartupOptions) -> ColorLogPrinter:
    return ColorLogPrinter(options.log_groups, options.hidden_groups)


def _build_llm_registry(config: Config, log: ColorLogPrinter, options: StartupOptions, token: InterruptToken) -> LLMRegistry:
    factory = ConfigurableLLMFactory(config.groq_api_key, config.openrouter_api_key)
    registry = LLMRegistry(factory)
    _register_slots(factory, config, log, registry, options, token)
    return registry


def _build_kernel(config: Config, log: ColorLogPrinter, options: StartupOptions, reporter: StatusReporterHub, token: InterruptToken) -> KernelAPI:
    return build_kernel(config, log, _build_llm_registry(config, log, options, token), reporter, token)


def _register_slots(factory: ConfigurableLLMFactory, config: Config, log: ColorLogPrinter, registry: LLMRegistry, options: StartupOptions, token: InterruptToken) -> None:
    registry.register_slot("gatekeeper", _slot_proxy(factory, config.gatekeeper_llm, log, "gatekeeper", options))
    registry.register_slot("stop_gate", _slot_proxy(factory, config.stop_gate_llm, log, "stop_gate", options))
    registry.register_slot("conversation_agent", _slot_proxy(factory, config.conversation_agent_llm, log, "conversation_agent", options, token))
    registry.register_slot("planner_agent", _slot_proxy(factory, config.planner_agent_llm, log, "planner_agent", options, token))
    registry.register_slot("executor_agent", _slot_proxy(factory, config.executor_agent_llm, log, "executor_agent", options, token))
    registry.register_slot("default_agent", _slot_proxy(factory, config.default_agent_llm, log, "default_agent", options, token))
    registry.register_slot("utility", _slot_proxy(factory, config.utility_llm, log, "utility", options))


def _slot_proxy(factory: ConfigurableLLMFactory, slot: object, log: ColorLogPrinter, name: str, options: StartupOptions, token: InterruptToken | None = None) -> LLMProxy:
    # the gatekeeper/utility slots get no token: they must stay usable while an interrupt is pending
    provider = factory.create(slot.provider_name, slot.model)
    return LLMProxy(provider, log, name, enabled_log_groups=options.log_groups, preview_chars=options.llm_log_preview_chars, interrupt_token=token)


def main() -> None:
    options = StartupOptions.from_sources(sys.argv[1:])
    config = Config.from_env()
    log = _build_log(options)
    reporter = StatusReporterHub(NullStatusSink(), log)
    kernel = _build_kernel(config, log, options, reporter, InterruptToken())
    reporter.set_models(kernel.get_llm_registry().model_labels())
    ShellLoader(config, kernel, log, reporter).start()


if __name__ == "__main__":
    main()
