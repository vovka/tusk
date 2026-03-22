from tusk.config import Config
from tusk.core.agent import MainAgent
from tusk.core.audio_capture import AudioCapture
from tusk.core.command_mode import CommandMode
from tusk.core.pipeline import Pipeline
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
from tusk.interfaces.stt_engine import STTEngine
from tusk.providers.groq_llm import GroqLLM
from tusk.providers.groq_stt import GroqSTT
from tusk.providers.open_router_llm import OpenRouterLLM
from tusk.providers.whisper_stt import WhisperSTT


def _build_stt(config: Config) -> STTEngine:
    if config.groq_api_key:
        print("[STT] using Groq whisper-large-v3-turbo")
        return GroqSTT(config.groq_api_key)
    print("[STT] using local Whisper")
    return WhisperSTT(config.whisper_model_size)


def _build_gatekeeper_llm(config: Config) -> LLMProvider:
    if config.groq_api_key:
        print("[GATE] using Groq llama-3.1-8b-instant")
        return GroqLLM(config.groq_api_key, "llama-3.1-8b-instant")
    return OpenRouterLLM(config.openrouter_api_key, config.gatekeeper_model)


def main() -> None:
    config = Config.from_env()
    audio = AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms)
    detector = UtteranceDetector(audio, config.audio_sample_rate, config.vad_aggressiveness)

    stt = _build_stt(config)
    gatekeeper = GnomeGatekeeper(_build_gatekeeper_llm(config))
    agent_llm = OpenRouterLLM(config.openrouter_api_key, config.main_agent_model)

    simulator = GnomeInputSimulator()
    clipboard = GnomeClipboardProvider()
    registry = build_tool_registry(simulator, clipboard, agent_llm)

    context = GnomeContextProvider(AppCatalog())
    agent = MainAgent(agent_llm, context, registry)
    command_mode = CommandMode(agent, registry)

    pipeline = Pipeline(
        utterance_detector=detector,
        stt_engine=stt,
        gatekeeper=gatekeeper,
        initial_mode=command_mode,
        config=config,
    )

    text_paster = GnomeTextPaster()
    factory = lambda: CommandMode(agent, registry)  # noqa: E731
    dictation_tool = DictationTool(pipeline, text_paster, agent_llm, factory)
    registry.register(dictation_tool)

    pipeline.run()


if __name__ == "__main__":
    main()
