import importlib.util
import json
import sys
import threading
from pathlib import Path

from shells.voice.stages.gatekeeper import LLMGatekeeper
from tusk.kernel import CommandMode, KernelAPI, LLMConversationSummarizer, MainAgent, SlidingWindowHistory, ToolRegistry
from tusk.kernel.adapter_manager import AdapterManager
from tusk.kernel.agent import AgentOrchestrator, FileAgentSessionStore
from tusk.kernel.agent_profiles import build_agent_profiles
from tusk.kernel.tool_runtime import ToolRuntime
from tusk.providers.llm import ConfigurableLLMFactory
from tusk.providers.stt import GroqSTT
from tusk.shared.config import Config, StartupOptions
from tusk.shared.llm import LLMProxy, LLMRegistry
from tusk.shared.logging import ColorLogPrinter


def _build_log(options: StartupOptions) -> ColorLogPrinter:
    return ColorLogPrinter(options.log_groups)


def _build_llm_registry(config: Config, log: ColorLogPrinter) -> LLMRegistry:
    factory = ConfigurableLLMFactory(config.groq_api_key, config.openrouter_api_key)
    registry = LLMRegistry(factory)
    _register_slots(factory, config, log, registry)
    return registry


def _register_slots(factory: ConfigurableLLMFactory, config: Config, log: ColorLogPrinter, registry: LLMRegistry) -> None:
    registry.register_slot("gatekeeper", _slot_proxy(factory, config.gatekeeper_llm, log, "gatekeeper"))
    registry.register_slot("conversation_agent", _slot_proxy(factory, config.conversation_agent_llm, log, "conversation_agent"))
    registry.register_slot("planner_agent", _slot_proxy(factory, config.planner_agent_llm, log, "planner_agent"))
    registry.register_slot("executor_agent", _slot_proxy(factory, config.executor_agent_llm, log, "executor_agent"))
    registry.register_slot("default_agent", _slot_proxy(factory, config.default_agent_llm, log, "default_agent"))
    registry.register_slot("utility", _slot_proxy(factory, config.utility_llm, log, "utility"))


def _build_kernel(config: Config, log: ColorLogPrinter) -> KernelAPI:
    llm_registry = _build_llm_registry(config, log)
    tool_registry = ToolRegistry()
    adapter_manager = _build_adapter_manager(config, log, tool_registry)
    history = SlidingWindowHistory(20, LLMConversationSummarizer(llm_registry.get("utility")))
    agent = _build_agent(config, log, llm_registry, tool_registry, history)
    kernel = KernelAPI(CommandMode(agent, log), llm_registry, log)
    ToolRuntime(tool_registry, llm_registry, adapter_manager, log).register_tools(kernel)
    return kernel


def _build_agent(config: Config, log: ColorLogPrinter, llm_registry: LLMRegistry, tool_registry: ToolRegistry, history: object) -> MainAgent:
    store = FileAgentSessionStore(config.agent_session_log_dir)
    profiles = build_agent_profiles(llm_registry)
    return MainAgent(AgentOrchestrator(profiles, tool_registry, store, log), history)


def _load_shells(config: Config, kernel: KernelAPI, log: ColorLogPrinter) -> list[object]:
    shells_dir = Path("shells")
    return [_load_shell(name, shells_dir, config, kernel, log) for name in config.shells]


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


def _slot_proxy(factory: ConfigurableLLMFactory, slot: object, log: ColorLogPrinter, name: str) -> LLMProxy:
    provider = factory.create(slot.provider_name, slot.model)
    return LLMProxy(provider, log, name)


def _load_shell(name: str, shells_dir: Path, config: Config, kernel: KernelAPI, log: ColorLogPrinter) -> object:
    manifest = json.loads((shells_dir / name / "shell.json").read_text())
    module_name = manifest["entry_module"]
    module = _load_module(shells_dir / name / f"{module_name}.py", f"shells.{name}.{module_name}")
    shell_class = getattr(module, manifest["entry_class"])
    if name != "voice":
        return shell_class()
    gatekeeper = LLMGatekeeper(kernel.get_llm_registry().get("gatekeeper"), log, follow_up_window_seconds=config.follow_up_timeout_seconds)
    return shell_class(config, log, stt_engine=GroqSTT(config.groq_api_key), gatekeeper=gatekeeper)


def main() -> None:
    options = StartupOptions.from_sources(sys.argv[1:])
    config = Config.from_env()
    log = _build_log(options)
    kernel = _build_kernel(config, log)
    shells = _load_shells(config, kernel, log)
    submit = kernel.submit
    for shell in shells[:-1]:
        threading.Thread(target=shell.start, args=(submit,), daemon=True).start()
    if shells:
        shells[-1].start(submit)


if __name__ == "__main__":
    main()
