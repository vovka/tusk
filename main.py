from tusk.config import Config
from tusk.core.agent import MainAgent
from tusk.core.audio_capture import AudioCapture
from tusk.core.color_log_printer import ColorLogPrinter
from tusk.core.command_mode import CommandMode
from tusk.core.llm_conversation_summarizer import LLMConversationSummarizer
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
from tusk.interfaces.log_printer import LogPrinter
from tusk.providers.groq_llm import GroqLLM
from tusk.providers.groq_stt import GroqSTT


def main() -> None:
    config = Config.from_env()
    log: LogPrinter = ColorLogPrinter()
    audio = AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms)
    detector = UtteranceDetector(audio, config.audio_sample_rate, config.vad_aggressiveness, log)

    stt = GroqSTT(config.groq_api_key)
    gatekeeper_llm = GroqLLM(config.groq_api_key, config.gatekeeper_model)
    agent_llm = GroqLLM(config.groq_api_key, config.main_agent_model)
    utility_llm = GroqLLM(config.groq_api_key, config.utility_model)

    gatekeeper = GnomeGatekeeper(gatekeeper_llm, log)
    simulator = GnomeInputSimulator()
    clipboard = GnomeClipboardProvider()
    registry = build_tool_registry(simulator, clipboard, utility_llm)

    context = GnomeContextProvider(AppCatalog())
    summarizer = LLMConversationSummarizer(utility_llm)
    history = SlidingWindowHistory(max_messages=20, summarizer=summarizer)
    agent = MainAgent(agent_llm, context, registry, history, log)
    command_mode = CommandMode(agent, log)

    pipeline = Pipeline(
        utterance_detector=detector,
        stt_engine=stt,
        gatekeeper=gatekeeper,
        initial_mode=command_mode,
        config=config,
        log_printer=log,
    )

    text_paster = GnomeTextPaster()
    factory = lambda: CommandMode(agent, log)  # noqa: E731
    dictation_tool = DictationTool(pipeline, text_paster, utility_llm, factory, log)
    registry.register(dictation_tool)

    pipeline.run()


if __name__ == "__main__":
    main()
