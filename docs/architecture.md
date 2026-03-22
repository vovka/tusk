# TUSK — Architecture

## System Overview

TUSK is an always-listening desktop AI voice assistant for Linux/GNOME. It captures
microphone audio continuously, detects speech boundaries, transcribes speech to text,
filters ambient noise via a fast gatekeeper LLM, passes confirmed commands to a capable
main agent LLM with desktop context, and executes actions via a configurable tool system.

The pipeline operates in **modes**. The default mode (command mode) filters and dispatches
voice commands. Dictation mode passes all speech through to a text field in real-time,
with LLM-based cleanup, until a stop command is detected.

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
    │   ├── agent_tool.py          # AgentTool ABC — self-describing, self-executing actions
    │   ├── pipeline_mode.py       # PipelineMode ABC — controls gatekeeper + routing
    │   ├── pipeline_controller.py # PipelineController ABC — mode switching interface
    │   └── text_paster.py         # TextPaster ABC — types text into desktop apps
    ├── schemas/                   # Frozen dataclasses for typed data flow
    │   ├── utterance.py
    │   ├── gate_result.py
    │   ├── tool_call.py           # Replaces SemanticAction — tool name + parameters
    │   ├── tool_result.py         # Execution outcome from a tool
    │   ├── desktop_context.py
    │   └── app_entry.py
    ├── core/                      # Pipeline orchestration
    │   ├── audio_capture.py
    │   ├── utterance_detector.py
    │   ├── agent.py               # Builds prompt from ToolRegistry, returns ToolCall
    │   ├── tool_registry.py       # Holds registered AgentTool instances
    │   ├── command_mode.py        # Default pipeline mode — gate → agent → tool
    │   ├── dictation_mode.py      # Dictation pipeline mode — paste + LLM cleanup
    │   └── pipeline.py            # Orchestrates STT + delegates to current mode
    ├── gnome/                     # GNOME/Linux implementations
    │   ├── gnome_gatekeeper.py
    │   ├── gnome_context_provider.py
    │   ├── gnome_text_paster.py   # xdotool-based text pasting and replacement
    │   ├── app_catalog.py
    │   └── tools/                 # AgentTool implementations
    │       ├── launch_application_tool.py
    │       ├── close_window_tool.py
    │       └── dictation_tool.py
    └── providers/                 # Pluggable STT and LLM implementations
        ├── whisper_stt.py
        ├── groq_stt.py
        ├── open_router_llm.py
        └── groq_llm.py
```

---

## Pipeline — Data Flow

### Command Mode (default)

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
CommandMode.handle_utterance()
    │
    ├─► Gatekeeper.evaluate(utterance, system_prompt)
    │       GateResult(is_directed_at_tusk, cleaned_command, confidence, metadata)
    │       — dropped if not directed at TUSK
    │
    └─► MainAgent.process_command()     agentic loop (up to 10 steps):
            ├─ LLM call with desktop context + tool history
            ├─ parse ToolCall → execute via ToolRegistry → append result
            └─ repeat until {"tool":"done"} or max steps reached
```

### Dictation Mode

```
STTEngine.transcribe()
    │
    ▼
DictationMode.handle_utterance()
    │
    ├─► Gatekeeper.evaluate(utterance, stop_detection_prompt)
    │       GateResult with metadata["metadata_stop"] = "true" if stop detected
    │
    ├─ if stop → GnomeTextPaster.replace() final cleanup → switch to CommandMode
    └─ if not stop → GnomeTextPaster.paste(raw_text)
                   → LLM cleanup of full buffer
                   → GnomeTextPaster.replace(char_count, cleaned_text)
```

---

## Interfaces (Abstract Base Classes)

Nine ABCs define the extension points. All swappable components implement one of these.

### `STTEngine` — `interfaces/stt_engine.py`

```python
def transcribe(self, audio_frames: bytes, sample_rate: int) -> Utterance
```

### `LLMProvider` — `interfaces/llm_provider.py`

```python
def complete(self, system_prompt: str, user_message: str) -> str
```

### `Gatekeeper` — `interfaces/gatekeeper.py`

```python
def evaluate(self, utterance: Utterance, system_prompt: str) -> GateResult
```

The `system_prompt` is provided by the current pipeline mode, allowing different
modes to ask different questions (command detection vs. stop detection).

### `ContextProvider` — `interfaces/context_provider.py`

```python
def get_context(self) -> DesktopContext
```

### `AgentTool` — `interfaces/agent_tool.py`

```python
@property def name(self) -> str
@property def description(self) -> str
@property def parameters_schema(self) -> dict[str, str]
def execute(self, parameters: dict[str, str]) -> ToolResult
```

Each tool is self-describing (name + description + parameter schema for the LLM prompt)
and self-executing. Adding a new action = one new class + one `registry.register()` call.

### `PipelineMode` — `interfaces/pipeline_mode.py`

```python
@property def gatekeeper_prompt(self) -> str
def handle_utterance(self, gate_result: GateResult, controller: PipelineController) -> None
```

Controls how utterances are processed. The gatekeeper prompt varies per mode.

### `PipelineController` — `interfaces/pipeline_controller.py`

```python
def set_mode(self, mode: PipelineMode) -> None
```

Implemented by `Pipeline`. Passed to modes so tools can trigger mode transitions
without holding a direct reference to the pipeline.

### `TextPaster` — `interfaces/text_paster.py`

```python
def paste(self, text: str) -> None
def replace(self, char_count: int, new_text: str) -> None
```

Types text into the currently focused desktop application. `replace` deletes
`char_count` characters backward then types `new_text`.

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
| `metadata` | `dict[str, str]` | Mode-specific signals (e.g. `{"metadata_stop": "true"}`) |

### `ToolCall`

| Field | Type | Description |
|---|---|---|
| `tool_name` | `str` | Name of the tool to invoke (matches `AgentTool.name`) |
| `parameters` | `dict[str, str]` | Parameters extracted from the LLM JSON response |

### `ToolResult`

| Field | Type | Description |
|---|---|---|
| `success` | `bool` | Whether the tool executed successfully |
| `message` | `str` | Human-readable outcome description |

### `DesktopContext`

| Field | Type | Description |
|---|---|---|
| `active_window_title` | `str` | Currently focused window title |
| `active_application` | `str` | Currently active application name |
| `open_windows` | `list[WindowInfo]` | All visible windows |
| `available_applications` | `list[AppEntry]` | All launchable applications |

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

### `UtteranceDetector` — `core/utterance_detector.py`

Consumes frames from `AudioCapture`. Uses `webrtcvad` to classify each frame as
voiced or unvoiced. Buffers voiced frames; when silence exceeds
`_SILENCE_FRAMES_THRESHOLD` (20 frames) after at least `_MIN_VOICED_FRAMES` (5) of
voiced audio, it yields an `Utterance`.

### `ToolRegistry` — `core/tool_registry.py`

Holds a `dict[str, AgentTool]` of registered tools. Provides `build_schema_text()`
which generates the JSON format descriptions injected into the agent's system prompt.

### `MainAgent` — `core/agent.py`

Receives a cleaned command string and runs a **multi-step agentic loop** (max 10 steps):
1. Builds a system prompt dynamically from `ToolRegistry`
2. Calls `LLMProvider.complete_messages()` with desktop context and message history
3. Parses the response into a `ToolCall` and executes it via `ToolRegistry`
4. Appends the tool result to message history and calls the LLM again
5. Stops when the LLM responds with `{"tool":"done"}` or max steps is reached

The agent has no knowledge of specific tools — it only knows the tool interface.
Multi-step commands ("select all and copy", "open Firefox and gedit") work naturally.

### `CommandMode` — `core/command_mode.py`

The default pipeline mode. Holds the wake-word detection gatekeeper prompt.
On each utterance: evaluates gatekeeper, if directed at TUSK delegates fully to
`MainAgent.process_command()`. All tool lookup and execution is owned by the agent.

### `DictationMode` — `core/dictation_mode.py`

Active when the user requests dictation. On each utterance:
1. Sends utterance to gatekeeper with a stop-detection prompt
2. If stop detected: triggers final cleanup, switches back to `CommandMode`
3. If not stop: pastes raw text immediately via `TextPaster.paste()`
4. Sends the full accumulated buffer to an LLM for cleanup (remove filler words,
   fix punctuation)
5. Replaces all previously pasted text with the cleaned version via
   `TextPaster.replace(char_count, cleaned_text)`

Text appears in the active field within ~1 second of each pause, then is silently
refined in place.

### `Pipeline` — `core/pipeline.py`

Implements `PipelineController`. Holds the current `PipelineMode` (starts as
`CommandMode`). For each utterance: runs STT, then delegates to the current mode's
`handle_utterance`. Mode switches are applied immediately via `set_mode()`.

---

## Agent Tools

Tools are registered in `ToolRegistry` at startup. The agent's LLM prompt is built
dynamically from all registered tools. Routing the LLM response to the correct tool
is done by matching `tool_name` against the registry.

### `LaunchApplicationTool` — `gnome/tools/launch_application_tool.py`

- **name:** `launch_application`
- **parameters:** `application_name` (exec_cmd from app catalog)
- **execution:** sends exec_cmd over Unix socket to host launcher daemon

### `CloseWindowTool` — `gnome/tools/close_window_tool.py`

- **name:** `close_window`
- **parameters:** `window_title` (exact title from window list)
- **execution:** runs `wmctrl -c <window_title>`

### `DictationTool` — `gnome/tools/dictation_tool.py`

- **name:** `start_dictation`
- **parameters:** none
- **execution:** calls `PipelineController.set_mode(DictationMode(...))` to enter
  dictation mode

---

## GNOME Implementations

### `GnomeGatekeeper` — `gnome/gnome_gatekeeper.py`

Calls `LLMProvider.complete()` with the system prompt supplied by the current
pipeline mode. Parses response JSON into `GateResult`. Extracts any `metadata_*`
fields from the JSON into `GateResult.metadata`.

Handles malformed responses: strips markdown code fences, unwraps nested arrays or
`"arguments"` keys, falls back to `is_directed_at_tusk=False` on parse failure.

### `GnomeContextProvider` — `gnome/gnome_context_provider.py`

Runs `wmctrl -l` to list open windows and `xdotool getactivewindow getwindowname`
to identify the focused window. Delegates application catalog to `AppCatalog`.

**External dependencies:** `wmctrl`, `xdotool` must be installed on the host.

### `GnomeTextPaster` — `gnome/gnome_text_paster.py`

- `paste(text)`: runs `xdotool type --delay 0 -- <text>`
- `replace(char_count, new_text)`: sends `char_count` BackSpace key events via
  `xdotool key`, then calls `paste(new_text)`

**External dependency:** `xdotool` must be installed on the host.

### `AppCatalog` — `gnome/app_catalog.py`

Scans `.desktop` files from standard XDG directories. Filters out hidden apps
and non-application entries. Cleans `Exec` strings and returns a sorted
`list[AppEntry]`.

---

## Provider Implementations

### `WhisperSTT` — `providers/whisper_stt.py`

Loads an OpenAI Whisper model locally. Computes confidence from segment
`avg_logprob` and `no_speech_prob`.

**Latency note:** Model load is one-time at startup; inference latency depends on
model size and hardware.

### `GroqSTT` — `providers/groq_stt.py`

Submits PCM audio (wrapped in WAV) to Groq's `whisper-large-v3-turbo`.
Detects hallucinations via regex; sets confidence to `0.0` for those.

### `OpenRouterLLM` — `providers/open_router_llm.py`

OpenAI-compatible client pointed at `https://openrouter.ai/api/v1`. Works with
any model available on OpenRouter.

### `GroqLLM` — `providers/groq_llm.py`

Native Groq SDK client. Used for low-latency gatekeeper classification.

---

## Host-Side Launcher — `launcher/tusk_host_launcher.py`

A standalone daemon running as the desktop user on the host. Listens on
`/tmp/tusk/launch.sock`. Spawns GUI applications via `subprocess.Popen` so they
appear in the desktop session (necessary because TUSK may run in a container).

---

## Dependency Injection & Wiring — `main.py`

`main.py` is the composition root. It reads `Config.from_env()`, selects concrete
implementations, and passes them into constructors:

```
Config.from_env()
    │
    ├── if GROQ_API_KEY → GroqSTT            else → WhisperSTT
    ├── if GROQ_API_KEY → GroqLLM            else → OpenRouterLLM   (gatekeeper)
    └── always          → OpenRouterLLM                             (agent + cleanup)

AppCatalog → GnomeContextProvider
GroqLLM / OpenRouterLLM → GnomeGatekeeper

ToolRegistry ← LaunchApplicationTool, CloseWindowTool
MainAgent(agent_llm, context, registry)
CommandMode(agent) → initial Pipeline mode

Pipeline(detector, stt, gatekeeper, CommandMode, config)

GnomeTextPaster
DictationTool(pipeline, text_paster, agent_llm, command_mode_factory)
  → registered into ToolRegistry

pipeline.run()   # infinite loop
```

No dependency is instantiated inside a class. Every class receives its dependencies
through `__init__`.

---

## Configuration — `tusk/config.py`

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | required | API key for OpenRouter |
| `GROQ_API_KEY` | `""` | API key for Groq (optional; enables Groq STT + LLM) |
| `GATEKEEPER_MODEL` | `liquid/lfm-2-24b-a2b` | Model for Tier 1 gatekeeper |
| `MAIN_AGENT_MODEL` | `x-ai/grok-4.1-fast` | Model for Tier 2 main agent |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model size: tiny / base / small / medium |
| `AUDIO_SAMPLE_RATE` | `16000` | Microphone sample rate in Hz |
| `AUDIO_FRAME_DURATION_MS` | `30` | VAD frame size in milliseconds |
| `VAD_AGGRESSIVENESS` | `2` | WebRTC VAD aggressiveness: 0 (least) – 3 (most) |

---

## Two-Tier LLM Design

**Tier 1 — Gatekeeper (cheap, fast):** Processes every transcribed utterance.
Its prompt is supplied by the current pipeline mode. In command mode it asks
"Is this for TUSK?" In dictation mode it asks "Is this a stop command?"

**Tier 2 — Main Agent (capable):** Only receives utterances the gatekeeper confirmed.
Reasons with full desktop context to produce a `ToolCall`. Invoked far less
frequently than the gatekeeper.

Both tiers use the same `LLMProvider` interface and can be independently configured.

---

## Extension Points

### Adding a New Action

1. Create a class implementing `AgentTool` in `tusk/gnome/tools/`
2. Add `registry.register(MyTool())` in `main.py`

No other files need to change. The agent's LLM prompt updates automatically.

### Adding a New Platform

Implement `ContextProvider` and the relevant `AgentTool`s for the platform.
Wire them in `main.py`.

### Adding a New Pipeline Mode

1. Create a class implementing `PipelineMode`
2. Create an `AgentTool` whose `execute` calls `controller.set_mode(MyMode(...))`
3. Register the tool in `main.py`

---

## External Tool Dependencies (GNOME)

| Tool | Purpose |
|---|---|
| `wmctrl` | List open windows, close windows by title |
| `xdotool` | Query active window title, type text, send keystrokes |

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
