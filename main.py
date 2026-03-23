from tusk.config import Config
from tusk.core.agent import MainAgent
from tusk.core.audio_capture import AudioCapture
from tusk.core.color_log_printer import ColorLogPrinter
from tusk.core.command_mode import CommandMode
from tusk.core.llm_conversation_summarizer import LLMConversationSummarizer
from tusk.core.monotonic_interaction_clock import MonotonicInteractionClock
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
from tusk.interfaces.llm_provider import LLMProvider
from tusk.interfaces.log_printer import LogPrinter
from tusk.interfaces.stt_engine import STTEngine
from tusk.providers.groq_llm import GroqLLM
from tusk.providers.groq_stt import GroqSTT
from tusk.providers.open_router_llm import OpenRouterLLM
from tusk.providers.whisper_stt import WhisperSTT


def _build_stt(config: Config, log: LogPrinter) -> STTEngine:
    if config.groq_api_key:
        log.log("STT", "using Groq whisper-large-v3-turbo")
        return GroqSTT(config.groq_api_key)
    log.log("STT", "using local Whisper")
    return WhisperSTT(config.whisper_model_size)


def _build_gatekeeper_llm(config: Config, log: LogPrinter) -> LLMProvider:
    if config.groq_api_key:
        log.log("GATE", "using Groq llama-3.1-8b-instant")
        return GroqLLM(config.groq_api_key, "llama-3.1-8b-instant")
    return OpenRouterLLM(config.openrouter_api_key, config.gatekeeper_model)


def main() -> None:
    config = Config.from_env()
    log: LogPrinter = ColorLogPrinter()
    audio = AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms)
    detector = UtteranceDetector(audio, config.audio_sample_rate, config.vad_aggressiveness, log)

    stt = _build_stt(config, log)
    gatekeeper = GnomeGatekeeper(_build_gatekeeper_llm(config, log), log)
    agent_llm = OpenRouterLLM(config.openrouter_api_key, config.main_agent_model)

    simulator = GnomeInputSimulator()
    clipboard = GnomeClipboardProvider()
    registry = build_tool_registry(simulator, clipboard, agent_llm)

    context = GnomeContextProvider(AppCatalog())
    summarizer = LLMConversationSummarizer(agent_llm)
    history = SlidingWindowHistory(max_messages=20, summarizer=summarizer)
    agent = MainAgent(agent_llm, context, registry, history, log)
    clock = MonotonicInteractionClock(config.follow_up_timeout_seconds)
    formatter = RecentContextFormatter(history)
    command_mode = CommandMode(agent, clock, formatter, log)

    pipeline = Pipeline(
        utterance_detector=detector,
        stt_engine=stt,
        gatekeeper=gatekeeper,
        initial_mode=command_mode,
        config=config,
        log_printer=log,
    )

    text_paster = GnomeTextPaster()
    factory = lambda: CommandMode(agent, clock, formatter, log)  # noqa: E731
    dictation_tool = DictationTool(pipeline, text_paster, agent_llm, factory, log)
    registry.register(dictation_tool)

    pipeline.run()


if __name__ == "__main__":
    main()
