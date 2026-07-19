"""Full-stack build for desktop e2e: real kernel, real gnome adapter, real Groq slots.

Unlike app_factory, this wires the adapters so commands reach the desktop;
the host launcher (launcher/tusk_host_launcher.py) must be running.
"""
import main as app_main
from tusk.kernel import KernelAPI, SlidingWindowHistory, ToolRegistry
from tusk.kernel.core.startup import build_adapter_manager, build_agent, build_api
from tusk.kernel.tools.tool_runtime import ToolRuntime
from tusk.shared.config import Config, StartupOptions
from tusk.shared.interrupt import InterruptToken
from tusk.shared.llm import LLMRegistry
from tusk.shared.logging import ColorLogPrinter
from tusk.shared.status import NullStatusSink, StatusReporterHub
from tusk.shared.tracing.null_tracer import NullTracer

__all__ = ["build_desktop_app"]


def build_desktop_app() -> tuple[KernelAPI, ToolRegistry, InterruptToken, ColorLogPrinter]:
    options = StartupOptions.from_sources([])
    config = Config.from_env()
    log = ColorLogPrinter(options.log_groups, options.hidden_groups)
    token = InterruptToken()
    llm_registry = app_main._build_llm_registry(config, log, options, token, NullTracer())
    kernel, tool_registry = _kernel(config, log, llm_registry, token)
    return kernel, tool_registry, token, log


def _kernel(config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, token: InterruptToken) -> tuple[KernelAPI, ToolRegistry]:
    reporter = StatusReporterHub(NullStatusSink(), log)
    tool_registry = ToolRegistry()
    adapter_manager = build_adapter_manager(config, log, tool_registry)
    agent = build_agent(config, log, llm_registry, tool_registry, SlidingWindowHistory(20), token, NullTracer())
    kernel = build_api(agent, config, log, llm_registry, reporter, token, NullTracer())
    ToolRuntime(tool_registry, llm_registry, adapter_manager, log, reporter).register_tools(kernel)
    return kernel, tool_registry
