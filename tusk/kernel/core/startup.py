from tusk.kernel import CommandMode, KernelAPI, MainAgent, SlidingWindowHistory, ToolRegistry
from tusk.kernel.core.adapter_manager import AdapterManager
from tusk.kernel.agent import AgentOrchestrator, FileStore
from tusk.kernel.agent.confirmation import ConfirmationGate
from tusk.kernel.interfaces.action_confirmation import ActionConfirmation
from tusk.kernel.agent.backends import AgentBackendFactory
from tusk.kernel.core.agent_profiles import build_agent_profiles
from tusk.kernel.tools.tool_runtime import ToolRuntime
from tusk.shared.config import Config
from tusk.shared.interrupt import InterruptToken
from tusk.shared.llm import LLMRegistry
from tusk.shared.logging import ColorLogPrinter
from tusk.shared.status import LatencyMeter, StatusReporterHub
from tusk.shared.tracing.interfaces.tracer import Tracer
from tusk.kernel.interfaces.conversation_history import ConversationHistory


def build_kernel(config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, reporter: StatusReporterHub, token: InterruptToken | None = None, tracer: Tracer | None = None, latency_meter: LatencyMeter | None = None) -> KernelAPI:
    tool_registry = ToolRegistry()
    adapter_manager = build_adapter_manager(config, log, tool_registry)
    history = SlidingWindowHistory(20)
    confirmation = ConfirmationGate(tool_registry, latency_meter=latency_meter)
    agent = build_agent(config, log, llm_registry, tool_registry, history, token, tracer, confirmation=confirmation)
    kernel = build_api(agent, config, log, llm_registry, reporter, token, tracer, confirmation=confirmation)
    ToolRuntime(tool_registry, llm_registry, adapter_manager, log, reporter).register_tools(kernel)
    return kernel


def build_api(agent: MainAgent, config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, reporter: StatusReporterHub, token: InterruptToken | None = None, tracer: Tracer | None = None, *, confirmation: ActionConfirmation) -> KernelAPI:
    backend = AgentBackendFactory(agent, config, log).create()
    command_mode = CommandMode(backend, log, confirmation)
    return KernelAPI(command_mode, llm_registry, log, reporter, token, tracer=tracer)


def build_agent(config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, tool_registry: ToolRegistry, history: ConversationHistory, token: InterruptToken | None = None, tracer: Tracer | None = None, *, confirmation: ActionConfirmation) -> MainAgent:
    store = FileStore(config.agent_session_log_dir)
    profiles = build_agent_profiles(llm_registry)
    return MainAgent(AgentOrchestrator(profiles, tool_registry, store, log, token, tracer, confirmation=confirmation), history, store)


def build_adapter_manager(config: Config, log: ColorLogPrinter, tool_registry: ToolRegistry) -> AdapterManager:
    manager = AdapterManager("adapters", tool_registry, log, config.adapter_env_cache_dir)
    manager.start_all()
    manager.start_watcher()
    return manager
