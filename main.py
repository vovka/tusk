import importlib.util
import json
import sys
import threading
from pathlib import Path

from tusk.kernel import (
    AdaptiveInteractionClock,
    ColorLogPrinter,
    CommandMode,
    Config,
    DailyFileLogger,
    HallucinationFilter,
    KernelAPI,
    LLMConversationSummarizer,
    LLMGatekeeper,
    LLMProxy,
    LLMRegistry,
    MainAgent,
    Pipeline,
    RecentContextFormatter,
    SlidingWindowHistory,
    StartupOptions,
    ToolRegistry,
)
from tusk.kernel.adapter_manager import AdapterManager
from tusk.kernel.providers.configurable_llm_factory import ConfigurableLLMFactory
from tusk.kernel.providers.groq_stt import GroqSTT
from tusk.kernel.tool_runtime import ToolRuntime


def _build_log(options: StartupOptions) -> ColorLogPrinter:
    return ColorLogPrinter(options.log_groups)


def _build_llm_registry(config: Config, log: ColorLogPrinter) -> LLMRegistry:
    factory = ConfigurableLLMFactory(config.groq_api_key, config.openrouter_api_key)
    registry = LLMRegistry(factory)
    registry.register_slot("gatekeeper", _slot_proxy(factory, config.gatekeeper_llm, log, "gatekeeper"))
    registry.register_slot("agent", _slot_proxy(factory, config.agent_llm, log, "agent"))
    registry.register_slot("utility", _slot_proxy(factory, config.utility_llm, log, "utility"))
    return registry


def _build_kernel(config: Config, log: ColorLogPrinter) -> KernelAPI:
    llm_registry = _build_llm_registry(config, log)
    tool_registry = ToolRegistry()
    adapter_manager = _build_adapter_manager(config, log, tool_registry)
    history = SlidingWindowHistory(20, LLMConversationSummarizer(llm_registry.get("utility")))
    logger = DailyFileLogger(config.conversation_log_dir)
    tools = ToolRuntime(config, tool_registry, llm_registry, adapter_manager, log)
    agent = MainAgent(llm_registry.get("agent"), tool_registry, history, log, tools.usage_recorder, logger)
    pipeline = _build_pipeline(config, log, llm_registry, history, agent)
    tools.register_tools(pipeline)
    return KernelAPI(pipeline, llm_registry, log)


def _load_shells(config: Config, api: KernelAPI) -> list[object]:
    shells_dir = Path("shells")
    loaded = []
    for name in config.shells:
        loaded.append(_load_shell(name, shells_dir, config, api))
    return loaded


def _load_module(path: Path, dotted_name: str) -> object:
    spec = importlib.util.spec_from_file_location(dotted_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _build_adapter_manager(config: Config, log: ColorLogPrinter, tool_registry: ToolRegistry) -> AdapterManager:
    manager = AdapterManager("adapters", tool_registry, log, config.adapter_env_cache_dir)
    manager.run_async(manager.start_all())
    manager.start_watcher()
    return manager


def _build_pipeline(
    config: Config,
    log: ColorLogPrinter,
    llm_registry: LLMRegistry,
    history: SlidingWindowHistory,
    agent: MainAgent,
) -> Pipeline:
    clock = AdaptiveInteractionClock(config.follow_up_timeout_seconds, config.max_follow_up_timeout_seconds)
    formatter = RecentContextFormatter(history)
    command_mode = CommandMode(agent, clock, formatter, log)
    gatekeeper = LLMGatekeeper(llm_registry.get("gatekeeper"), log)
    return Pipeline(GroqSTT(config.groq_api_key), HallucinationFilter(), gatekeeper, command_mode, None, config, log)


def _slot_proxy(factory: ConfigurableLLMFactory, slot: object, log: ColorLogPrinter, name: str) -> LLMProxy:
    provider = factory.create(slot.provider_name, slot.model)
    return LLMProxy(provider, log, name)



def _load_shell(name: str, shells_dir: Path, config: Config, api: KernelAPI) -> object:
    manifest = json.loads((shells_dir / name / "shell.json").read_text())
    module_name = manifest["entry_module"]
    module = _load_module(shells_dir / name / f"{module_name}.py", f"shells.{name}.{module_name}")
    shell_class = getattr(module, manifest["entry_class"])
    return shell_class(config, api._log) if name == "voice" else shell_class()


def main() -> None:
    options = StartupOptions.from_sources(sys.argv[1:])
    config = Config.from_env()
    log = _build_log(options)
    kernel_api = _build_kernel(config, log)
    shells = _load_shells(config, kernel_api)
    for shell in shells[:-1]:
        threading.Thread(target=shell.start, args=(kernel_api,), daemon=True).start()
    if shells:
        shells[-1].start(kernel_api)


if __name__ == "__main__":
    main()
