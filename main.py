from tusk.config import Config
from tusk.core.audio_capture import AudioCapture
from tusk.core.color_log_printer import ColorLogPrinter
from tusk.core.command_mode import CommandMode
from tusk.core.agent_message_compactor import AgentMessageCompactor
from tusk.core.daily_file_logger import DailyFileLogger
from tusk.core.hallucination_filter import HallucinationFilter
from tusk.core.llm_conversation_summarizer import LLMConversationSummarizer
from tusk.core.llm_proxy import LLMProxy
from tusk.core.llm_registry import LLMRegistry
from tusk.core.agent import MainAgent
from tusk.core.adaptive_interaction_clock import AdaptiveInteractionClock
from tusk.core.recent_context_formatter import RecentContextFormatter
from tusk.core.pipeline import Pipeline
from tusk.core.sliding_window_history import SlidingWindowHistory
from tusk.core.utterance_detector import UtteranceDetector
from tusk.gnome.app_catalog import AppCatalog
from tusk.gnome.gnome_clipboard_provider import GnomeClipboardProvider
from tusk.gnome.gnome_context_provider import GnomeContextProvider
from tusk.gnome.gnome_gatekeeper import GnomeGatekeeper
from tusk.gnome.gnome_input_simulator import GnomeInputSimulator
from tusk.gnome.gnome_text_paster import GnomeTextPaster
from tusk.gnome.tool_factory import build_tool_registry
from tusk.gnome.tools.dictation_tool import DictationTool
from tusk.core.tool_registry import ToolRegistry
from tusk.interfaces.llm_provider_factory import LLMProviderFactory
from tusk.interfaces.log_printer import LogPrinter
from tusk.providers.configurable_llm_factory import ConfigurableLLMFactory
from tusk.providers.groq_stt import GroqSTT
from tusk.schemas.llm_slot_config import LLMSlotConfig


def _build_llm_registry(config: Config, log: LogPrinter | None = None) -> LLMRegistry:
    factory = ConfigurableLLMFactory(config.groq_api_key, config.openrouter_api_key)
    registry = LLMRegistry(factory)
    _register_slot(registry, factory, "gatekeeper", config.gatekeeper_llm, log)
    _register_slot(registry, factory, "agent", config.agent_llm, log)
    _register_slot(registry, factory, "utility", config.utility_llm, log)
    return registry


def _register_slot(
    registry: LLMRegistry,
    factory: LLMProviderFactory,
    name: str,
    slot_config: LLMSlotConfig,
    log: LogPrinter | None = None,
) -> None:
    provider = factory.create(slot_config.provider_name, slot_config.model)
    registry.register_slot(name, LLMProxy(provider, log))


def _build_pipeline(config: Config, log: LogPrinter) -> Pipeline:
    audio = AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms)
    detector = UtteranceDetector(audio, config.audio_sample_rate, config.vad_aggressiveness, log)
    stt = GroqSTT(config.groq_api_key)
    llm_registry = _build_llm_registry(config, log)

    gatekeeper = GnomeGatekeeper(llm_registry.get("gatekeeper"), log)
    simulator = GnomeInputSimulator()
    clipboard = GnomeClipboardProvider()
    tool_registry = build_tool_registry(simulator, clipboard, llm_registry.get("utility"), llm_registry)

    context = GnomeContextProvider(AppCatalog())
    summarizer = LLMConversationSummarizer(llm_registry.get("utility"))
    history = SlidingWindowHistory(max_messages=40, summarizer=summarizer)
    compactor = AgentMessageCompactor()
    logger = DailyFileLogger(config.conversation_log_directory)
    agent = MainAgent(llm_registry.get("agent"), context, tool_registry, history, log, compactor, logger)
    clock = AdaptiveInteractionClock(config.follow_up_timeout_seconds, config.max_follow_up_timeout_seconds)
    formatter = RecentContextFormatter(history)
    command_mode = CommandMode(agent, clock, formatter, log)

    utterance_filter = HallucinationFilter()
    pipeline = Pipeline(
        utterance_detector=detector, stt_engine=stt, gatekeeper=gatekeeper,
        utterance_filter=utterance_filter, initial_mode=command_mode,
        config=config, log_printer=log,
    )

    _register_dictation(tool_registry, pipeline, llm_registry, agent, clock, formatter, log)
    return pipeline


def _register_dictation(
    tool_registry: ToolRegistry,
    pipeline: Pipeline,
    llm_registry: LLMRegistry,
    agent: MainAgent,
    clock: AdaptiveInteractionClock,
    formatter: RecentContextFormatter,
    log: LogPrinter,
) -> None:
    text_paster = GnomeTextPaster()
    factory = lambda: CommandMode(agent, clock, formatter, log)  # noqa: E731
    dictation = DictationTool(pipeline, text_paster, llm_registry.get("utility"), factory, log)
    tool_registry.register(dictation)


def main() -> None:
    config = Config.from_env()
    log: LogPrinter = ColorLogPrinter()
    pipeline = _build_pipeline(config, log)
    pipeline.run()


if __name__ == "__main__":
    main()
