import main as app_main
from tusk.kernel import CommandMode, KernelAPI, MainAgent, SlidingWindowHistory, ToolRegistry
from tusk.kernel.agent import AgentOrchestrator, FileStore
from tusk.kernel.agent_profiles import build_agent_profiles
from tusk.shared.config import Config, StartupOptions
from tusk.shared.interrupt import InterruptToken
from tusk.shared.llm import LLMRegistry
from tusk.shared.logging import ColorLogPrinter

__all__ = ["build_app"]


def build_app() -> tuple[KernelAPI, InterruptToken, ColorLogPrinter]:
    """Real kernel + real Groq LLM slots; no MCP adapters so e2e never touches the desktop."""
    options = StartupOptions.from_sources([])
    config = Config.from_env()
    log = ColorLogPrinter(options.log_groups, options.hidden_groups)
    token = InterruptToken()
    registry = app_main._build_llm_registry(config, log, options, token)
    return _kernel(config, log, registry, token), token, log


def _kernel(config: Config, log: ColorLogPrinter, registry: LLMRegistry, token: InterruptToken) -> KernelAPI:
    history = SlidingWindowHistory(20)
    store = FileStore(config.agent_session_log_dir)
    orchestrator = AgentOrchestrator(build_agent_profiles(registry), ToolRegistry(), store, log, token)
    return KernelAPI(CommandMode(MainAgent(orchestrator, history), log), registry, log, None, token)
