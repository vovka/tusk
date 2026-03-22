# TUSK — Architecture

## System Overview

TUSK is an always-listening desktop AI voice assistant for Linux/GNOME. It captures
microphone audio continuously, detects speech boundaries, transcribes speech to text,
filters ambient noise via a fast gatekeeper LLM, passes confirmed commands to a capable
main agent LLM with desktop context, and executes semantic actions on the desktop.

---

## Directory Structure

```
tusk/
├── main.py                        # Entry point — wires all components
├── requirements.txt
├── .env.example
├── launcher/
│   └── tusk_host_launcher.py      # Host-side daemon for launching applications
└── tusk/
    ├── config.py                  # Immutable Config dataclass, loaded from env
    ├── interfaces/                # Abstract base classes (extension points)
    │   ├── stt_engine.py
    │   ├── llm_provider.py
    │   ├── gatekeeper.py
    │   ├── context_provider.py
    │   └── action_executor.py
    ├── schemas/                   # Frozen dataclasses for typed data flow
    │   ├── utterance.py
    │   ├── gate_result.py
    │   ├── semantic_action.py
    │   ├── desktop_context.py
    │   └── app_entry.py
    ├── core/                      # Pipeline orchestration
    │   ├── audio_capture.py
    │   ├── utterance_detector.py
    │   ├── agent.py
    │   └── pipeline.py
    ├── gnome/                     # GNOME/Linux implementations
    │   ├── gnome_gatekeeper.py
    │   ├── gnome_context_provider.py
    │   ├── gnome_action_executor.py
    │   └── app_catalog.py
    └── providers/                 # Pluggable STT and LLM implementations
        ├── whisper_stt.py
        ├── groq_stt.py
        ├── open_router_llm.py
        └── groq_llm.py
```

---

## Pipeline — Data Flow

Each spoken utterance passes through five sequential stages:

```
Microphone
    │
    ▼
AudioCapture                    streams raw PCM frames (int16, mono, 16 kHz)
    │
    ▼
UtteranceDetector               WebRTC VAD; buffers voiced frames, yields on silence
    │  Utterance(text="", audio_frames, duration)
    ▼
STTEngine.transcribe()          Whisper (local) or Groq cloud Whisper
    │  Utterance(text, confidence)
    │  — dropped if confidence < 0.01
    ▼
Gatekeeper.evaluate()           LLM binary classification: "Is this for TUSK?"
    │  GateResult(is_directed_at_tusk, cleaned_command, confidence)
    │  — dropped if not directed at TUSK
    ▼
MainAgent.process_command()     LLM + desktop context → SemanticAction (JSON)
    │  SemanticAction (LaunchApplicationAction | CloseWindowAction | UnrecognizedAction)
    ▼
ActionExecutor.execute()        Sends launch command via Unix socket, or wmctrl -c
```

---

## Interfaces (Abstract Base Classes)

Five ABCs define the extension points. All swappable components implement one of these.

### `STTEngine` — `interfaces/stt_engine.py`

```python
def transcribe(self, audio_frames: bytes, sample_rate: int) -> Utterance
```

Converts raw PCM audio to transcribed text with a confidence score.

### `LLMProvider` — `interfaces/llm_provider.py`

```python
def complete(self, system_prompt: str, user_message: str) -> str
```

Makes a single completion call to any LLM. Used by both the gatekeeper and main agent.

### `Gatekeeper` — `interfaces/gatekeeper.py`

```python
def evaluate(self, utterance: Utterance) -> GateResult
```

Decides whether the utterance is directed at TUSK and strips the wake word.

### `ContextProvider` — `interfaces/context_provider.py`

```python
def get_context(self) -> DesktopContext
```

Observes the desktop environment and returns structured state for the agent.

### `ActionExecutor` — `interfaces/action_executor.py`

```python
def execute(self, action: SemanticAction) -> None
```

Translates a semantic action into platform-specific desktop operations.

---

## Schemas — Typed Data Containers

All inter-component data uses frozen dataclasses (immutable, type-safe).

### `Utterance`

| Field | Type | Description |
|---|---|---|
| `text` | `str` | Transcribed text (empty before STT) |
| `audio_frames` | `bytes` | Raw PCM audio |
| `duration_seconds` | `float` | Duration of the utterance |
| `confidence` | `float` | STT confidence score (0.0–1.0) |

### `GateResult`

| Field | Type | Description |
|---|---|---|
| `is_directed_at_tusk` | `bool` | Whether the utterance targets TUSK |
| `cleaned_command` | `str` | Text with wake word removed |
| `confidence` | `float` | Gatekeeper confidence |

### `SemanticAction`

A `Union` of three frozen dataclasses, discriminated by `action_type`:

| Variant | Fields |
|---|---|
| `LaunchApplicationAction` | `action_type="launch_application"`, `application_name: str` |
| `CloseWindowAction` | `action_type="close_window"`, `window_title: str` |
| `UnrecognizedAction` | `action_type="unknown"`, `reason: str` |

### `DesktopContext`

| Field | Type | Description |
|---|---|---|
| `active_window_title` | `str` | Currently focused window title |
| `active_application` | `str` | Currently active application name |
| `open_windows` | `list[WindowInfo]` | All visible windows |
| `available_applications` | `list[AppEntry]` | All launchable applications |

### `WindowInfo`

| Field | Type | Description |
|---|---|---|
| `window_id` | `str` | X11 window identifier |
| `title` | `str` | Window title |
| `application` | `str` | Application name |
| `is_active` | `bool` | Whether this window is focused |

### `AppEntry`

| Field | Type | Description |
|---|---|---|
| `name` | `str` | User-visible application name |
| `exec_cmd` | `str` | Launch command (e.g. `firefox`) |

---

## Core Components

### `AudioCapture` — `core/audio_capture.py`

Streams raw PCM from the system microphone using `sounddevice.RawInputStream`.
Yields fixed-size frames (configurable via `audio_frame_duration_ms`).
Runs indefinitely; no internal state beyond the stream handle.

### `UtteranceDetector` — `core/utterance_detector.py`

Consumes frames from `AudioCapture`. Uses `webrtcvad` to classify each frame as
voiced or unvoiced. Buffers voiced frames; when silence exceeds
`_SILENCE_FRAMES_THRESHOLD` (20 frames) after at least `_MIN_VOICED_FRAMES` (5) of
voiced audio, it yields an `Utterance` with empty text and the buffered PCM.

### `MainAgent` — `core/agent.py`

Receives a cleaned command string. Calls `ContextProvider.get_context()` to collect
current desktop state, builds a user message combining the command and context, calls
`LLMProvider.complete()` with a JSON-instructing system prompt, and parses the
response into a `SemanticAction`.

The system prompt instructs the LLM to respond with exactly one JSON object matching
one of the three action variants.

### `Pipeline` — `core/pipeline.py`

The main event loop. Iterates over utterances from `UtteranceDetector`, runs each
through STT, gatekeeper, agent, and executor in sequence. Handles exceptions per
utterance so a single failure does not halt the loop.

---

## GNOME Implementations

### `GnomeGatekeeper` — `gnome/gnome_gatekeeper.py`

Calls `LLMProvider.complete()` with a prompt asking whether the text is directed at
TUSK (by mention of "tusk"/"task" or by being an imperative desktop command).
Expected LLM response: `{"directed": bool, "cleaned_command": str}`.

Handles malformed responses: strips markdown code fences, unwraps nested arrays or
`"arguments"` keys, falls back to `is_directed_at_tusk=False` on parse failure.

Wake-word stripping removes "hey tusk", "tusk", "hey task", "task" prefixes from the
cleaned command.

### `GnomeContextProvider` — `gnome/gnome_context_provider.py`

Runs `wmctrl -l` to list open windows and `xdotool getactivewindow getwindowname` to
identify the focused window. Delegates application catalog to `AppCatalog`.

**External dependencies:** `wmctrl`, `xdotool` must be installed on the host.

### `GnomeActionExecutor` — `gnome/gnome_action_executor.py`

- **Launch:** Sends the `exec_cmd` string over a Unix domain socket at
  `/tmp/tusk/launch.sock` to the host-side launcher daemon. Waits for `"ok"` or an
  error response.
- **Close:** Runs `wmctrl -c <window_title>` as a subprocess.
- **Unrecognized:** Prints the reason; no desktop action taken.

### `AppCatalog` — `gnome/app_catalog.py`

Scans `.desktop` files from standard XDG directories
(`/usr/share/applications`, `/usr/local/share/applications`, `~/.local/share/applications`).
Filters out hidden apps (`NoDisplay=true`) and non-application entries.
Cleans `Exec` strings by removing `%`-placeholders and taking the first token.
Returns a sorted `list[AppEntry]`.

---

## Provider Implementations

### `WhisperSTT` — `providers/whisper_stt.py`

Loads an OpenAI Whisper model locally (`tiny` / `base` / `small` / `medium`).
Decodes int16 PCM to float32, runs `whisper.transcribe(fp16=False, language="en")`.
Computes confidence from segment `avg_logprob` and `no_speech_prob`.

**Latency note:** Model load is one-time at startup; inference latency depends on model
size and available hardware.

### `GroqSTT` — `providers/groq_stt.py`

Wraps PCM in a WAV container and submits it to Groq's hosted
`whisper-large-v3-turbo` model. Detects hallucinations (e.g. `[BLANK_AUDIO]`,
`[Music]`) via regex and sets confidence to `0.0` for those.

### `OpenRouterLLM` — `providers/open_router_llm.py`

OpenAI-compatible client pointed at `https://openrouter.ai/api/v1`. Sends a
`chat.completions` request with `max_tokens=256`. Identifies itself via
`HTTP-Referer` and `X-Title` headers. Works with any model available on OpenRouter.

### `GroqLLM` — `providers/groq_llm.py`

Native Groq SDK client. Same interface as `OpenRouterLLM`. Used for low-latency
gatekeeper classification via Groq's fast inference.

---

## Host-Side Launcher — `launcher/tusk_host_launcher.py`

A standalone daemon that runs as the desktop user on the host (outside the container).
It listens on `/tmp/tusk/launch.sock`. For each connection it:

1. Reads the command string (up to 4096 bytes).
2. Parses it with `shlex.split()`.
3. Spawns the process via `subprocess.Popen` (fire-and-forget).
4. Responds with `"ok\n"` or an error message.

**Why it exists:** The TUSK container runs as an unprivileged user and cannot directly
launch GUI applications as the desktop session owner. The launcher runs on the host
with the user's session environment so spawned apps appear in the desktop session.

---

## Dependency Injection & Wiring — `main.py`

`main.py` is the composition root. It reads `Config.from_env()`, selects concrete
implementations based on environment variables, and passes them into constructors:

```
Config.from_env()
    │
    ├── if GROQ_API_KEY → GroqSTT         else → WhisperSTT
    ├── if GROQ_API_KEY → GroqLLM         else → OpenRouterLLM   (gatekeeper)
    └── always          → OpenRouterLLM                           (main agent)

AppCatalog → GnomeContextProvider
GroqLLM / OpenRouterLLM → GnomeGatekeeper
OpenRouterLLM + GnomeContextProvider → MainAgent
GnomeActionExecutor

AudioCapture + UtteranceDetector → Pipeline(stt, gatekeeper, agent, executor, config)
pipeline.run()   # infinite loop
```

No dependency is instantiated inside a class. Every class receives its dependencies
through `__init__`.

---

## Configuration — `tusk/config.py`

All configuration lives in a single frozen dataclass loaded from environment variables.

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | required | API key for OpenRouter |
| `GROQ_API_KEY` | `""` | API key for Groq (optional; enables Groq STT + LLM) |
| `GATEKEEPER_MODEL` | `liquid/lfm-2-24b-a2b` | Model for Tier 1 gatekeeper (OpenRouter ID) |
| `MAIN_AGENT_MODEL` | `x-ai/grok-4.1-fast` | Model for Tier 2 main agent (OpenRouter ID) |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model size: tiny / base / small / medium |
| `AUDIO_SAMPLE_RATE` | `16000` | Microphone sample rate in Hz |
| `AUDIO_FRAME_DURATION_MS` | `30` | VAD frame size in milliseconds |
| `VAD_AGGRESSIVENESS` | `2` | WebRTC VAD aggressiveness: 0 (least) – 3 (most) |

---

## Two-Tier LLM Design

**Tier 1 — Gatekeeper (cheap, fast):** Processes every transcribed utterance. Its sole
job is binary classification: "Is this for TUSK?" Ambient speech, background TV,
and casual conversation are discarded here. Default: a small, low-latency model.

**Tier 2 — Main Agent (capable):** Only receives utterances the gatekeeper confirmed.
Reasons with full desktop context to produce a structured action. Default: a more
capable model. Invoked far less frequently than the gatekeeper.

Both tiers use the same `LLMProvider` interface and can be independently configured to
any model or provider (Groq, OpenRouter, local, etc.).

---

## Extension Points

To support a new platform, implement these two ABCs and wire them in `main.py`:

| ABC | Replace | With |
|---|---|---|
| `ContextProvider` | `GnomeContextProvider` | Windows/macOS equivalent |
| `ActionExecutor` | `GnomeActionExecutor` | Windows/macOS equivalent |

To replace the STT or LLM backend, implement `STTEngine` or `LLMProvider` respectively.

The core (`pipeline.py`, `agent.py`, `utterance_detector.py`, `audio_capture.py`)
requires no modification when adding new platforms or providers.

---

## External Tool Dependencies (GNOME)

| Tool | Purpose |
|---|---|
| `wmctrl` | List open windows, close windows by title |
| `xdotool` | Query active window title |

These must be installed on the host system.

## Python Library Dependencies

| Library | Purpose |
|---|---|
| `openai-whisper` | Local STT inference |
| `sounddevice` | Microphone audio capture |
| `webrtcvad` | Voice activity detection |
| `numpy` | PCM audio decoding for Whisper |
| `openai` | OpenRouter client (OpenAI-compatible API) |
| `groq` | Groq API client (STT + LLM) |
