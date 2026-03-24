import sys
import types
from types import SimpleNamespace


def _stub_module(name: str, module: types.ModuleType) -> None:
    if name not in sys.modules:
        sys.modules[name] = module


def pytest_sessionstart(session) -> None:
    _stub_sounddevice()
    _stub_webrtcvad()
    _stub_whisper()
    _stub_groq()
    _stub_openai()


def _stub_sounddevice() -> None:
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, frame): return b"\x00\x00" * frame, None
    mod = types.ModuleType("sounddevice")
    mod.RawInputStream = lambda **kwargs: Stream()
    _stub_module("sounddevice", mod)


def _stub_webrtcvad() -> None:
    class Vad:
        def __init__(self, aggressiveness): self.flag = aggressiveness
        def is_speech(self, frame, sample_rate): return bool(frame)
    mod = types.ModuleType("webrtcvad")
    mod.Vad = Vad
    _stub_module("webrtcvad", mod)


def _stub_whisper() -> None:
    class Model:
        def transcribe(self, array, fp16, language):
            return {"text": "ok", "segments": [{"avg_logprob": -0.2, "no_speech_prob": 0.1}]}
    mod = types.ModuleType("whisper")
    mod.load_model = lambda model_size: Model()
    _stub_module("whisper", mod)


def _stub_groq() -> None:
    class Groq:
        def __init__(self, **kwargs):
            msg = SimpleNamespace(content='{"tool":"done"}')
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **k: SimpleNamespace(choices=[SimpleNamespace(message=msg)])))
            trans = SimpleNamespace(create=lambda **k: SimpleNamespace(text="hello"))
            self.audio = SimpleNamespace(transcriptions=trans)
    mod = types.ModuleType("groq")
    mod.Groq = Groq
    _stub_module("groq", mod)


def _stub_openai() -> None:
    class OpenAI:
        def __init__(self, **kwargs):
            msg = SimpleNamespace(content='{"tool":"done"}')
            create = lambda **k: SimpleNamespace(choices=[SimpleNamespace(message=msg)])
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))
    mod = types.ModuleType("openai")
    mod.OpenAI = OpenAI
    _stub_module("openai", mod)
