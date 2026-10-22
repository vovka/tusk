"""Real kernel + real Groq LLM slots for e2e runs.

with_adapters=False skips the MCP adapters so the voice e2e never touches the desktop;
with_adapters=True wires the gnome adapter and needs launcher/tusk_host_launcher.py running.
"""
from tusk.kernel import KernelAPI, ToolRegistry
from tusk.kernel.core.startup import build_kernel
from tusk.providers.llm import ConfigurableLLMFactory
from tusk.shared.config import Config, StartupOptions
from tusk.shared.interrupt_token import InterruptToken
from tusk.shared.llm import LLMRegistryBuilder
from tusk.shared.observability import ColorLogPrinter, NullStatusSink, StatusReporter
from tusk.shared.observability.null_tracer import NullTracer

__all__ = ["build_app"]


def build_app(with_adapters: bool) -> tuple[KernelAPI, ToolRegistry, InterruptToken, ColorLogPrinter]:
    options = StartupOptions.from_sources([])
    config = Config.from_env()
    log = ColorLogPrinter(options.log_groups, options.hidden_groups)
    token = InterruptToken()
    factory = ConfigurableLLMFactory(config.groq_api_key, config.openrouter_api_key)
    llm_registry = LLMRegistryBuilder(factory, config, log, options, token, NullTracer()).build()
    reporter = StatusReporter(NullStatusSink(), log)
    tool_registry = ToolRegistry()
    kernel = build_kernel(config, log, llm_registry, reporter, token, tool_registry=tool_registry, with_adapters=with_adapters)
    return kernel, tool_registry, token, log
