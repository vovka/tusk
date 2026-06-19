import sys

from shell_loader import ShellLoader
from tusk.kernel import CommandMode, KernelAPI, LLMConversationSummarizer, MainAgent, SlidingWindowHistory, ToolRegistry
from tusk.kernel.adapter_manager import AdapterManager
from tusk.kernel.agent import AgentOrchestrator, FileAgentSessionStore
from tusk.kernel.agent_profiles import build_agent_profiles
from tusk.kernel.tool_runtime import ToolRuntime
from tusk.providers.llm import ConfigurableLLMFactory
from tusk.shared.config import Config, StartupOptions
from tusk.shared.llm import LLMProxy, LLMRegistry
from tusk.shared.logging import ColorLogPrinter
from tusk.shared.status import NullStatusSink, StatusReporterHub


def _build_log(options: StartupOptions) -> ColorLogPrinter:
    return ColorLogPrinter(options.log_groups, options.hidden_groups)


def _build_llm_registry(config: Config, log: ColorLogPrinter, options: StartupOptions) -> LLMRegistry:
    factory = ConfigurableLLMFactory(config.groq_api_key, config.openrouter_api_key)
    registry = LLMRegistry(factory)
    _register_slots(factory, config, log, registry, options)
    return registry


def _register_slots(factory: ConfigurableLLMFactory, config: Config, log: ColorLogPrinter, registry: LLMRegistry, options: StartupOptions) -> None:
    registry.register_slot("gatekeeper", _slot_proxy(factory, config.gatekeeper_llm, log, "gatekeeper", options))
    registry.register_slot("conversation_agent", _slot_proxy(factory, config.conversation_agent_llm, log, "conversation_agent", options))
    registry.register_slot("planner_agent", _slot_proxy(factory, config.planner_agent_llm, log, "planner_agent", options))
    registry.register_slot("executor_agent", _slot_proxy(factory, config.executor_agent_llm, log, "executor_agent", options))
    registry.register_slot("default_agent", _slot_proxy(factory, config.default_agent_llm, log, "default_agent", options))
    registry.register_slot("utility", _slot_proxy(factory, config.utility_llm, log, "utility", options))


def _build_kernel(config: Config, log: ColorLogPrinter, options: StartupOptions, reporter: StatusReporterHub) -> KernelAPI:
    llm_registry = _build_llm_registry(config, log, options)
    tool_registry = ToolRegistry()
    adapter_manager = _build_adapter_manager(config, log, tool_registry)
    history = SlidingWindowHistory(20, LLMConversationSummarizer(llm_registry.get("utility")))
    agent = _build_agent(config, log, llm_registry, tool_registry, history)
    kernel = KernelAPI(CommandMode(agent, log), llm_registry, log, reporter)
    ToolRuntime(tool_registry, llm_registry, adapter_manager, log, reporter).register_tools(kernel)
    return kernel


def _build_agent(config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, tool_registry: ToolRegistry, history: object) -> MainAgent:
    store = FileAgentSessionStore(config.agent_session_log_dir)
    profiles = build_agent_profiles(llm_registry)
    return MainAgent(AgentOrchestrator(profiles, tool_registry, store, log), history)


def _build_adapter_manager(config: Config, log: ColorLogPrinter, tool_registry: ToolRegistry) -> AdapterManager:
    manager = AdapterManager("adapters", tool_registry, log, config.adapter_env_cache_dir)
    manager.run_async(manager.start_all())
    manager.start_watcher()
    return manager


def _slot_proxy(factory: ConfigurableLLMFactory, slot: object, log: ColorLogPrinter, name: str, options: StartupOptions) -> LLMProxy:
    provider = factory.create(slot.provider_name, slot.model)
    return LLMProxy(provider, log, name, enabled_log_groups=options.log_groups, preview_chars=options.llm_log_preview_chars)


def main() -> None:
    options = StartupOptions.from_sources(sys.argv[1:])
    config = Config.from_env()
    log = _build_log(options)
    reporter = StatusReporterHub(NullStatusSink(), log)
    kernel = _build_kernel(config, log, options, reporter)
    reporter.set_models(kernel.get_llm_registry().model_labels())
    ShellLoader(config, kernel, log, reporter).start()


if __name__ == "__main__":
    main()
