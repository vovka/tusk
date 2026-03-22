from tusk.config import Config
from tusk.core.audio_capture import AudioCapture
from tusk.core.agent import MainAgent
from tusk.core.pipeline import Pipeline
from tusk.core.utterance_detector import UtteranceDetector
from tusk.gnome.app_catalog import AppCatalog
from tusk.gnome.gnome_action_executor import GnomeActionExecutor
from tusk.gnome.gnome_context_provider import GnomeContextProvider
from tusk.gnome.gnome_gatekeeper import GnomeGatekeeper
from tusk.providers.open_router_llm import OpenRouterLLM
from tusk.providers.whisper_stt import WhisperSTT


def main() -> None:
    config = Config.from_env()

    audio_capture = AudioCapture(config.audio_sample_rate, config.audio_frame_duration_ms)
    utterance_detector = UtteranceDetector(audio_capture, config.audio_sample_rate, config.vad_aggressiveness)

    stt_engine = WhisperSTT(config.whisper_model_size)

    gatekeeper_llm = OpenRouterLLM(config.openrouter_api_key, config.gatekeeper_model)
    agent_llm = OpenRouterLLM(config.openrouter_api_key, config.main_agent_model)

    gatekeeper = GnomeGatekeeper(gatekeeper_llm)
    context_provider = GnomeContextProvider(AppCatalog())
    main_agent = MainAgent(agent_llm, context_provider)
    action_executor = GnomeActionExecutor()

    pipeline = Pipeline(
        utterance_detector=utterance_detector,
        stt_engine=stt_engine,
        gatekeeper=gatekeeper,
        main_agent=main_agent,
        action_executor=action_executor,
        config=config,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
