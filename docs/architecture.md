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
    │   ├── llm_provider_factory.py # Creates LLMProvider instances by provider name
    │   ├── gatekeeper.py
    │   ├── context_provider.py
    │   ├── agent_tool.py          # AgentTool ABC — self-describing, self-executing actions
    │   ├── pipeline_mode.py       # PipelineMode ABC — controls gatekeeper + routing
    │   ├── pipeline_controller.py # PipelineController ABC — mode switching interface
    │   ├── text_paster.py         # TextPaster ABC — types text into desktop apps
    │   ├── input_simulator.py     # InputSimulator ABC — keys, mouse, typing
    │   ├── clipboard_provider.py  # ClipboardProvider ABC — read/write clipboard
    │   ├── interaction_clock.py   # InteractionClock ABC — follow-up window tracking
    │   ├── conversation_history.py    # ConversationHistory ABC — message storage
    │   ├── conversation_summarizer.py # ConversationSummarizer ABC — compacts history
    │   └── log_printer.py         # LogPrinter ABC — tagged log output
    ├── schemas/                   # Frozen dataclasses for typed data flow
    │   ├── utterance.py
    │   ├── gate_result.py
    │   ├── tool_call.py           # Tool name + parameters
    │   ├── tool_result.py         # Execution outcome from a tool
    │   ├── desktop_context.py     # Includes WindowInfo
    │   ├── app_entry.py
    │   ├── chat_message.py        # role + content for conversation history
    │   └── llm_slot_config.py     # provider_name + model parsed from "provider/model"
    ├── core/                      # Pipeline orchestration
    │   ├── audio_capture.py
    │   ├── utterance_detector.py
    │   ├── agent.py               # Multi-step agentic loop with tool calling
    │   ├── tool_registry.py       # Holds registered AgentTool instances
    │   ├── command_mode.py        # Default pipeline mode — gate → agent → tool
    │   ├── dictation_mode.py      # Dictation pipeline mode — paste + LLM cleanup
    │   ├── pipeline.py            # Orchestrates STT + delegates to current mode
    │   ├── llm_proxy.py           # Swappable wrapper around LLMProvider
    │   ├── llm_registry.py        # Manages named LLM slots (gatekeeper/agent/utility)
    │   ├── sliding_window_history.py      # ConversationHistory with auto-summarization
    │   ├── llm_conversation_summarizer.py # Summarizes old messages via LLM
    │   ├── monotonic_interaction_clock.py  # InteractionClock via time.monotonic()
    │   ├── recent_context_formatter.py    # Formats recent messages for gatekeeper
    │   └── color_log_printer.py   # Colored terminal log output
    ├── gnome/                     # GNOME/Linux implementations
    │   ├── gnome_gatekeeper.py
    │   ├── gnome_context_provider.py
    │   ├── gnome_text_paster.py   # xdotool-based text pasting and replacement
    │   ├── gnome_input_simulator.py  # xdotool-based keys, mouse, typing
    │   ├── gnome_clipboard_provider.py # xclip-based clipboard read/write
    │   ├── app_catalog.py
    │   ├── tool_factory.py        # Builds and registers all GNOME tools
    │   └── tools/                 # AgentTool implementations (19 tools)
    │       ├── launch_application_tool.py
    │       ├── close_window_tool.py
    │       ├── focus_window_tool.py
    │       ├── maximize_window_tool.py
    │       ├── minimize_window_tool.py
    │       ├── move_resize_window_tool.py
    │       ├── switch_workspace_tool.py
    │       ├── press_keys_tool.py
    │       ├── type_text_tool.py
    │       ├── mouse_click_tool.py
    │       ├── mouse_move_tool.py
    │       ├── mouse_drag_tool.py
    │       ├── mouse_scroll_tool.py
    │       ├── read_clipboard_tool.py
    │       ├── write_clipboard_tool.py
    │       ├── open_uri_tool.py
    │       ├── dictation_tool.py
    │       ├── ai_transform_tool.py
    │       └── switch_model_tool.py
    └── providers/                 # Pluggable STT and LLM implementations
        ├── whisper_stt.py
        ├── groq_stt.py
        ├── open_router_llm.py
        ├── groq_llm.py
        └── configurable_llm_factory.py  # LLMProviderFactory for groq + openrouter
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

Fifteen ABCs define the extension points. All swappable components implement one of these.

### `STTEngine` — `interfaces/stt_engine.py`

```python
def transcribe(self, audio_frames: bytes, sample_rate: int) -> Utterance
```

### `LLMProvider` — `interfaces/llm_provider.py`

```python
@property def label(self) -> str
def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str
def complete_messages(self, system_prompt: str, messages: list[dict]) -> str
```

`label` returns a human-readable identifier (e.g. `"groq/llama-3.1-8b-instant"`).
`complete_messages` is used by the multi-step agent loop, which maintains a message
history across tool-call iterations.

### `LLMProviderFactory` — `interfaces/llm_provider_factory.py`

```python
def create(self, provider_name: str, model: str) -> LLMProvider
```

Creates `LLMProvider` instances by provider name (e.g. `"groq"`, `"openrouter"`).
Used by `LLMRegistry` when swapping models at runtime.

### `Gatekeeper` — `interfaces/gatekeeper.py`

```python
def evaluate(self, utterance: Utterance, system_prompt: str) -> GateResult
```

The `system_prompt` is provided by the current pipeline mode, allowing different
modes to ask different questions (command detection vs. stop detection).

### `InteractionClock` — `interfaces/interaction_clock.py`

```python
def record_interaction(self) -> None
def seconds_since_last_interaction(self) -> float
def is_within_follow_up_window(self) -> bool
```

Tracks when the last successful command was processed. Used by `CommandMode` to
determine whether the gatekeeper prompt should include recent conversation context
for follow-up detection. The follow-up window is configurable via
`FOLLOW_UP_TIMEOUT_SECONDS` (default 30 seconds).

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
def handle_utterance(self, gate_result: GateResult, utterance: Utterance, controller: PipelineController) -> None
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

### `InputSimulator` — `interfaces/input_simulator.py`

```python
def press_keys(self, keys: str) -> None
def type_text(self, text: str) -> None
def mouse_click(self, x: int, y: int, button: int, clicks: int) -> None
def mouse_move(self, x: int, y: int) -> None
def mouse_drag(self, from_x: int, from_y: int, to_x: int, to_y: int, button: int) -> None
def mouse_scroll(self, direction: str, clicks: int) -> None
```

Abstracts all keyboard and mouse input. Implemented by `GnomeInputSimulator` via
`xdotool`. Used by input and mouse tools.

### `ClipboardProvider` — `interfaces/clipboard_provider.py`

```python
def read(self) -> str
def write(self, text: str) -> None
```

Read/write system clipboard. Implemented by `GnomeClipboardProvider` via `xclip`.

### `ConversationHistory` — `interfaces/conversation_history.py`

```python
def get_messages(self) -> list[ChatMessage]
def append(self, message: ChatMessage) -> None
def clear(self) -> None
```

Stores the agent's message history within a session. Implemented by
`SlidingWindowHistory` with auto-summarization.

### `ConversationSummarizer` — `interfaces/conversation_summarizer.py`

```python
def summarize(self, messages: list[ChatMessage]) -> str
```

Compresses old messages into a summary string. Used by `SlidingWindowHistory`
when the history exceeds its capacity.

### `LogPrinter` — `interfaces/log_printer.py`

```python
def log(self, tag: str, message: str) -> None
```

Tagged log output. Implemented by `ColorLogPrinter` for colored terminal display.

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

### `WindowInfo`

| Field | Type | Description |
|---|---|---|
| `window_id` | `str` | X11 window identifier |
| `title` | `str` | Window title |
| `application` | `str` | Application name |
| `is_active` | `bool` | Whether this is the focused window |
| `x` | `int` | Window X position (default 0) |
| `y` | `int` | Window Y position (default 0) |
| `width` | `int` | Window width (default 0) |
| `height` | `int` | Window height (default 0) |

### `AppEntry`

| Field | Type | Description |
|---|---|---|
| `name` | `str` | User-visible application name |
| `exec_cmd` | `str` | Launch command (e.g. `firefox`) |

### `ChatMessage`

| Field | Type | Description |
|---|---|---|
| `role` | `str` | Message role (`"user"`, `"assistant"`, `"system"`) |
| `content` | `str` | Message text |

Property `is_summary` returns `True` if the content starts with `"Previous context summary: "`.

### `LLMSlotConfig`

| Field | Type | Description |
|---|---|---|
| `provider_name` | `str` | Provider identifier (e.g. `"groq"`, `"openrouter"`) |
| `model` | `str` | Model identifier (e.g. `"llama-3.1-8b-instant"`) |

`LLMSlotConfig.parse("groq/llama-3.1-8b-instant")` splits on the first `/`.

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

The default pipeline mode. Builds the gatekeeper prompt dynamically based on
conversation state. When within the follow-up window (configurable, default 30s),
the prompt includes recent conversation context so the gatekeeper can recognize
contextual follow-ups without a wake word. Outside the window, the prompt is the
standard wake-word detection prompt.

On each utterance: evaluates gatekeeper, if directed at TUSK delegates fully to
`MainAgent.process_command()` and records the interaction on the `InteractionClock`.
All tool lookup and execution is owned by the agent.

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

### `MonotonicInteractionClock` — `core/monotonic_interaction_clock.py`

Implements `InteractionClock` using `time.monotonic()`. Tracks the timestamp of the
last successful command execution and determines whether the conversation is within
the follow-up window.

### `RecentContextFormatter` — `core/recent_context_formatter.py`

Extracts the last N messages (default 6) from `ConversationHistory` and formats them
as compact text for injection into the gatekeeper prompt. Each message is truncated
to 150 characters. No LLM call — pure string formatting (< 1 ms).

### `LLMProxy` — `core/llm_proxy.py`

Wraps an `LLMProvider` and delegates all calls to it. Exposes a `swap(provider)`
method that replaces the inner provider at runtime. All consumers hold a reference
to the proxy, so swapping is transparent. Used by `LLMRegistry` for hot-swapping.

### `LLMRegistry` — `core/llm_registry.py`

Manages named LLM slots (`"gatekeeper"`, `"agent"`, `"utility"`). Each slot holds
an `LLMProxy`. `swap(slot_name, provider_name, model)` creates a new provider via
`LLMProviderFactory` and calls `proxy.swap()`. Used by `SwitchModelTool` for
runtime model switching via voice command.

### `SlidingWindowHistory` — `core/sliding_window_history.py`

Implements `ConversationHistory`. Holds up to `max_messages` (default 20). When
capacity is exceeded, evicts the oldest 50% of messages, summarizes them via
`ConversationSummarizer`, and inserts the summary as a single message at the front.

### `LLMConversationSummarizer` — `core/llm_conversation_summarizer.py`

Implements `ConversationSummarizer`. Formats evicted messages as a transcript and
calls the utility LLM to produce a one-paragraph summary.

### `ColorLogPrinter` — `core/color_log_printer.py`

Implements `LogPrinter`. Outputs tagged, colored log lines to the terminal.

### `Pipeline` — `core/pipeline.py`

Implements `PipelineController`. Holds the current `PipelineMode` (starts as
`CommandMode`). For each utterance: runs STT, then delegates to the current mode's
`handle_utterance`. Mode switches are applied immediately via `set_mode()`.

---

## Agent Tools

Tools are registered in `ToolRegistry` at startup via `ToolFactory.build_tool_registry()`.
The agent's LLM prompt is built dynamically from all registered tools. Routing the LLM
response to the correct tool is done by matching `tool_name` against the registry.

There are 19 tools organized into categories:

### Application & Window Management

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `LaunchApplicationTool` | `launch_application` | `application_name` | Sends exec_cmd over Unix socket to host launcher |
| `CloseWindowTool` | `close_window` | `window_title` | `wmctrl -c <title>` |
| `FocusWindowTool` | `focus_window` | `window_title` | `wmctrl -a <title>` |
| `MaximizeWindowTool` | `maximize_window` | `window_title` | `wmctrl` add maximized state |
| `MinimizeWindowTool` | `minimize_window` | `window_title` | `xdotool` find + minimize |
| `MoveResizeWindowTool` | `move_resize_window` | `window_title`, `geometry` | `wmctrl -e <geometry>` |
| `SwitchWorkspaceTool` | `switch_workspace` | `workspace_number` | `wmctrl -s <n>` |

### Input Simulation

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `PressKeysTool` | `press_keys` | `keys` | `InputSimulator.press_keys()` |
| `TypeTextTool` | `type_text` | `text` | `InputSimulator.type_text()` |

### Mouse Control

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `MouseClickTool` | `mouse_click` | `x`, `y`, `button`, `clicks` | `InputSimulator.mouse_click()` |
| `MouseMoveTool` | `mouse_move` | `x`, `y` | `InputSimulator.mouse_move()` |
| `MouseDragTool` | `mouse_drag` | `from_x`, `from_y`, `to_x`, `to_y` | `InputSimulator.mouse_drag()` |
| `MouseScrollTool` | `mouse_scroll` | `direction`, `clicks` | `InputSimulator.mouse_scroll()` |

### Clipboard

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `ReadClipboardTool` | `read_clipboard` | *(none)* | `ClipboardProvider.read()` |
| `WriteClipboardTool` | `write_clipboard` | `text` | `ClipboardProvider.write()` |

### Desktop Navigation

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `OpenUriTool` | `open_uri` | `uri` | `xdg-open <uri>` |

### Special Modes & System

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `DictationTool` | `start_dictation` | *(none)* | Switches pipeline to `DictationMode` |
| `AiTransformTool` | `ai_transform` | `instruction` | Copies selection, applies LLM transform, replaces |
| `SwitchModelTool` | `switch_model` | `slot`, `provider`, `model` | `LLMRegistry.swap()` for runtime model switching |

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

### `GnomeInputSimulator` — `gnome/gnome_input_simulator.py`

Implements `InputSimulator`. All operations use `xdotool`:

- `press_keys(keys)` — `xdotool key`
- `type_text(text)` — `xdotool type --delay 0`
- `mouse_click(x, y, button, clicks)` — `xdotool mousemove` + `xdotool click`
- `mouse_move(x, y)` — `xdotool mousemove`
- `mouse_drag(from_x, from_y, to_x, to_y, button)` — `xdotool mousemove` + button down/up
- `mouse_scroll(direction, clicks)` — `xdotool click` (button 4/5 for up/down)

### `GnomeClipboardProvider` — `gnome/gnome_clipboard_provider.py`

Implements `ClipboardProvider` via `xclip` (clipboard selection, not primary).

- `read()` — `xclip -selection clipboard -o`
- `write(text)` — pipes text to `xclip -selection clipboard`

### `ToolFactory` — `gnome/tool_factory.py`

`build_tool_registry()` creates a `ToolRegistry` and registers all 19 tools,
injecting their dependencies. Organizes registration into logical groups via
helper functions (`_register_input_tools`, `_register_window_tools`, etc.).

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

### `ConfigurableLLMFactory` — `providers/configurable_llm_factory.py`

Implements `LLMProviderFactory`. Supports two provider names: `"groq"` and
`"openrouter"`. Takes both API keys at construction. Called by `LLMRegistry` when
creating or swapping providers at runtime.

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
    ├── ConfigurableLLMFactory(groq_key, openrouter_key)
    │
    ├── LLMRegistry ← 3 slots, each an LLMProxy:
    │   ├── "gatekeeper" → parse(GATEKEEPER_LLM)  default: groq/llama-3.1-8b-instant
    │   ├── "agent"      → parse(AGENT_LLM)       default: groq/openai/gpt-oss-120b
    │   └── "utility"    → parse(UTILITY_LLM)      default: groq/llama-3.3-70b-versatile
    │
    ├── GroqSTT(groq_key)
    ├── GnomeGatekeeper(registry.get("gatekeeper"))
    ├── GnomeInputSimulator, GnomeClipboardProvider
    ├── build_tool_registry(simulator, clipboard, utility_llm, llm_registry)  → 19 tools
    │
    ├── AppCatalog → GnomeContextProvider
    ├── LLMConversationSummarizer(utility_llm)
    ├── SlidingWindowHistory(max=20, summarizer)
    ├── MainAgent(agent_llm, context, tool_registry, history)
    ├── MonotonicInteractionClock(follow_up_timeout)
    ├── RecentContextFormatter(history)
    ├── CommandMode(agent, clock, formatter) → initial mode
    │
    ├── Pipeline(detector, stt, gatekeeper, command_mode, config)
    │
    └── DictationTool(pipeline, text_paster, utility_llm, command_mode_factory)
        → registered into ToolRegistry after pipeline construction

pipeline.run()   # infinite loop
```

No dependency is instantiated inside a class. Every class receives its dependencies
through `__init__`.

---

## Configuration — `tusk/config.py`

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | API key for Groq (STT + LLM) |
| `OPENROUTER_API_KEY` | `""` | API key for OpenRouter (optional) |
| `GATEKEEPER_LLM` | `groq/llama-3.1-8b-instant` | Gatekeeper slot (`provider/model`) |
| `AGENT_LLM` | `groq/openai/gpt-oss-120b` | Main agent slot (`provider/model`) |
| `UTILITY_LLM` | `groq/llama-3.3-70b-versatile` | Utility slot for summaries/cleanup (`provider/model`) |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model size: tiny / base / small / medium |
| `AUDIO_SAMPLE_RATE` | `16000` | Microphone sample rate in Hz |
| `AUDIO_FRAME_DURATION_MS` | `30` | VAD frame size in milliseconds |
| `VAD_AGGRESSIVENESS` | `2` | WebRTC VAD aggressiveness: 0 (least) – 3 (most) |
| `FOLLOW_UP_TIMEOUT_SECONDS` | `30` | Seconds after last command before follow-up window expires |

LLM slot values use `provider/model` format, parsed by `LLMSlotConfig.parse()`.
The provider portion after the first `/` is passed to `ConfigurableLLMFactory`.

---

## Three-Slot LLM Design

All LLM consumers are served by three named slots managed by `LLMRegistry`. Each
slot wraps an `LLMProxy` so models can be swapped at runtime via the
`switch_model` tool (voice command: "Tusk, use Opus for the agent").

**Gatekeeper slot (cheap, fast):** Processes every transcribed utterance.
Its prompt is supplied by the current pipeline mode. In command mode the prompt is
built dynamically: it asks "Is this for TUSK?" and, when within the follow-up window
(default 30 seconds since last command), also includes recent conversation context so
the gatekeeper can recognize contextual follow-ups without a wake word.
In dictation mode it asks "Is this a stop command?"

**Agent slot (capable):** Only receives utterances the gatekeeper confirmed.
Reasons with full desktop context and runs a multi-step agentic loop. Invoked far
less frequently than the gatekeeper.

**Utility slot:** Used for conversation summarization (history compaction) and
dictation text cleanup. Not on the hot path for command latency.

All three slots use the same `LLMProvider` interface and can be independently
configured via environment variables or switched at runtime.

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
| `wmctrl` | List/close/focus/maximize/move/resize windows, switch workspaces |
| `xdotool` | Query active window, type text, send keystrokes, mouse control |
| `xclip` | Read/write system clipboard |
| `xdg-open` | Open URLs and file paths with default application |

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
