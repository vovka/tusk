import importlib.util
import json
import threading
from pathlib import Path

from tusk.kernel import (
    ColorLogPrinter,
    CommandMode,
    Config,
    KernelAPI,
    LLMConversationSummarizer,
    LLMGatekeeper,
    LLMProxy,
    LLMRegistry,
    MainAgent,
    MonotonicInteractionClock,
    Pipeline,
    RecentContextFormatter,
    SlidingWindowHistory,
    ToolRegistry,
)
from tusk.kernel.adapter_manager import AdapterManager
from tusk.kernel.internal_tools import DictationRouter, StartDictationTool, SwitchModelTool
from tusk.kernel.providers.configurable_llm_factory import ConfigurableLLMFactory
from tusk.kernel.providers.groq_stt import GroqSTT


def _build_log() -> ColorLogPrinter:
    return ColorLogPrinter()


def _build_llm_registry(config: Config, log: ColorLogPrinter) -> LLMRegistry:
    factory = ConfigurableLLMFactory(config.groq_api_key, config.openrouter_api_key)
    registry = LLMRegistry(factory)
    registry.register_slot("gatekeeper", LLMProxy(factory.create(config.gatekeeper_llm.provider_name, config.gatekeeper_llm.model), log))
    registry.register_slot("agent", LLMProxy(factory.create(config.agent_llm.provider_name, config.agent_llm.model), log))
    registry.register_slot("utility", LLMProxy(factory.create(config.utility_llm.provider_name, config.utility_llm.model), log))
    return registry


def _build_kernel(config: Config, log: ColorLogPrinter) -> KernelAPI:
    llm_registry = _build_llm_registry(config, log)
    tool_registry = ToolRegistry()
    adapter_manager = AdapterManager("adapters", tool_registry, log, config.adapter_env_cache_dir)
    adapter_manager.run_async(adapter_manager.start_all())
    adapter_manager.start_watcher()
    history = SlidingWindowHistory(20, LLMConversationSummarizer(llm_registry.get("utility")))
    agent = MainAgent(llm_registry.get("agent"), tool_registry, history, adapter_manager, log)
    clock = MonotonicInteractionClock(config.follow_up_timeout_seconds)
    formatter = RecentContextFormatter(history)
    command_mode = CommandMode(agent, clock, formatter, log)
    pipeline = Pipeline(
        stt_engine=GroqSTT(config.groq_api_key),
        gatekeeper=LLMGatekeeper(llm_registry.get("gatekeeper"), log),
        command_mode=command_mode,
        dictation_router=None,
        config=config,
        log_printer=log,
    )
    pipeline._dictation_router = DictationRouter(tool_registry, pipeline)
    tool_registry.register(SwitchModelTool(llm_registry))
    tool_registry.register(StartDictationTool(tool_registry, pipeline, adapter_manager))
    return KernelAPI(pipeline, llm_registry, log)


def _load_shells(config: Config, api: KernelAPI) -> list[object]:
    shells_dir = Path("shells")
    loaded = []
    for name in config.shells:
        manifest = json.loads((shells_dir / name / "shell.json").read_text())
        module = _load_module(shells_dir / name / f"{manifest['entry_module']}.py", f"shells.{name}.{manifest['entry_module']}")
        cls = getattr(module, manifest["entry_class"])
        if name == "voice":
            loaded.append(cls(config, api._log))
        else:
            loaded.append(cls())
    return loaded


def _load_module(path: Path, dotted_name: str) -> object:
    spec = importlib.util.spec_from_file_location(dotted_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    config = Config.from_env()
    log = _build_log()
    kernel_api = _build_kernel(config, log)
    shells = _load_shells(config, kernel_api)
    for shell in shells[:-1]:
        threading.Thread(target=shell.start, args=(kernel_api,), daemon=True).start()
    if shells:
        shells[-1].start(kernel_api)


if __name__ == "__main__":
    main()
