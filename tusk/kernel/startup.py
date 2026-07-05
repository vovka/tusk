from tusk.kernel import CommandMode, KernelAPI, LLMConversationSummarizer, MainAgent, SlidingWindowHistory, ToolRegistry
from tusk.kernel.adapter_manager import AdapterManager
from tusk.kernel.agent import AgentOrchestrator, FileAgentSessionStore
from tusk.kernel.agent_backends import AgentBackendFactory
from tusk.kernel.agent_profiles import build_agent_profiles
from tusk.kernel.tool_runtime import ToolRuntime
from tusk.shared.config import Config
from tusk.shared.llm import LLMRegistry
from tusk.shared.logging import ColorLogPrinter
from tusk.shared.status import StatusReporterHub


def build_kernel(config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, reporter: StatusReporterHub) -> KernelAPI:
    tool_registry = ToolRegistry()
    adapter_manager = build_adapter_manager(config, log, tool_registry)
    history = SlidingWindowHistory(20, LLMConversationSummarizer(llm_registry.get("utility")))
    agent = build_agent(config, log, llm_registry, tool_registry, history)
    kernel = build_api(agent, config, log, llm_registry, reporter)
    ToolRuntime(tool_registry, llm_registry, adapter_manager, log, reporter).register_tools(kernel)
    return kernel


def build_api(agent: MainAgent, config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, reporter: StatusReporterHub) -> KernelAPI:
    backend = AgentBackendFactory(agent, config, log).create()
    return KernelAPI(CommandMode(backend, log), llm_registry, log, reporter)


def build_agent(config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, tool_registry: ToolRegistry, history: object) -> MainAgent:
    store = FileAgentSessionStore(config.agent_session_log_dir)
    profiles = build_agent_profiles(llm_registry)
    return MainAgent(AgentOrchestrator(profiles, tool_registry, store, log), history)


def build_adapter_manager(config: Config, log: ColorLogPrinter, tool_registry: ToolRegistry) -> AdapterManager:
    manager = AdapterManager("adapters", tool_registry, log, config.adapter_env_cache_dir)
    manager.run_async(manager.start_all())
    manager.start_watcher()
    return manager
