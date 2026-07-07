from tusk.kernel import CommandMode, KernelAPI, LLMConversationSummarizer, MainAgent, SlidingWindowHistory, ToolRegistry
from tusk.kernel.adapter_manager import AdapterManager
from tusk.kernel.agent import AgentOrchestrator, FileAgentSessionStore
from tusk.kernel.agent_backends import AgentBackendFactory
from tusk.kernel.agent_profiles import build_agent_profiles
from tusk.kernel.tool_runtime import ToolRuntime
from tusk.shared.config import Config
from tusk.shared.interrupt import InterruptToken
from tusk.shared.llm import LLMRegistry
from tusk.shared.logging import ColorLogPrinter
from tusk.shared.status import StatusReporterHub


def build_kernel(config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, reporter: StatusReporterHub, token: InterruptToken | None = None) -> KernelAPI:
    tool_registry = ToolRegistry()
    adapter_manager = build_adapter_manager(config, log, tool_registry)
    history = SlidingWindowHistory(20, LLMConversationSummarizer(llm_registry.get("utility")))
    agent = build_agent(config, log, llm_registry, tool_registry, history, token)
    kernel = build_api(agent, config, log, llm_registry, reporter, token)
    ToolRuntime(tool_registry, llm_registry, adapter_manager, log, reporter).register_tools(kernel)
    return kernel


def build_api(agent: MainAgent, config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, reporter: StatusReporterHub, token: InterruptToken | None = None) -> KernelAPI:
    backend = AgentBackendFactory(agent, config, log).create()
    return KernelAPI(CommandMode(backend, log), llm_registry, log, reporter, token)


def build_agent(config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, tool_registry: ToolRegistry, history: object, token: InterruptToken | None = None) -> MainAgent:
    store = FileAgentSessionStore(config.agent_session_log_dir)
    profiles = build_agent_profiles(llm_registry)
    return MainAgent(AgentOrchestrator(profiles, tool_registry, store, log, token), history)


def build_adapter_manager(config: Config, log: ColorLogPrinter, tool_registry: ToolRegistry) -> AdapterManager:
    manager = AdapterManager("adapters", tool_registry, log, config.adapter_env_cache_dir)
    manager.start_all()
    manager.start_watcher()
    return manager
