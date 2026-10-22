import os
import sys

from shell_loader import ShellLoader
from tusk import __version__
from tusk.kernel import KernelAPI
from tusk.kernel.core.startup import build_kernel
from tusk.providers.llm import ConfigurableLLMFactory
from tusk.shared.config import Config, StartupOptions
from tusk.shared.interfaces.tracer import Tracer
from tusk.shared.interrupt_token import InterruptToken
from tusk.shared.llm import LLMRegistryBuilder
from tusk.shared.observability import ColorLogPrinter, LatencyMeter, NullStatusSink, StatusReporter, TracerFactory


def main() -> None:
    options = StartupOptions.from_sources(sys.argv[1:])
    _check_version_flag(options)
    config = Config.from_env()
    log = ColorLogPrinter(options.log_groups, options.hidden_groups)
    tracer = TracerFactory().create(os.environ.get("TRACING_OTLP_ENDPOINT", ""))
    reporter = StatusReporter(NullStatusSink(), log)
    latency_meter = LatencyMeter(log, reporter)
    kernel = _build_kernel(config, log, options, reporter, InterruptToken(), tracer, latency_meter)
    reporter.set_models(kernel.llm_registry.model_labels())
    ShellLoader(config, kernel, log, reporter, latency_meter.mark_speech_end).start()


def _check_version_flag(options: StartupOptions) -> None:
    if options.version:
        print(__version__)
        sys.exit(0)


def _build_kernel(config: Config, log: ColorLogPrinter, options: StartupOptions, reporter: StatusReporter, token: InterruptToken, tracer: Tracer, latency_meter: LatencyMeter) -> KernelAPI:
    factory = ConfigurableLLMFactory(config.groq_api_key, config.openrouter_api_key)
    llm_registry = LLMRegistryBuilder(factory, config, log, options, token, tracer).build()
    return build_kernel(config, log, llm_registry, reporter, token, tracer, latency_meter)


if __name__ == "__main__":
    main()
