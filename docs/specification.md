# TUSK — Technical Specification

This document describes the implemented system as it exists in code. It is a precise,
component-by-component specification derived from the actual implementation.

---

## 1. System Boundaries

TUSK runs as a Python process (optionally inside Docker). It interacts with:

- **Microphone** — via `sounddevice` (reads from default input device)
- **LLM APIs** — via HTTPS to OpenRouter and/or Groq
- **Desktop environment** — via `wmctrl`, `xdotool`, `xclip`, and `xdg-open` subprocesses
- **Host launcher daemon** — via a Unix domain socket at `/tmp/tusk/launch.sock`

The host launcher daemon (`launcher/tusk_host_launcher.py`) is a separate process that
must run on the host with access to the desktop session.

---

## 2. Configuration Specification

**Source:** `tusk/config.py` — `Config` dataclass, populated by `Config.from_env()`.

All values are read from environment variables at startup. The `Config` object is
immutable (`frozen=True`) for the lifetime of the process.

### 2.1 Required Fields

| Env Var | Type | Description |
|---|---|---|
| `GROQ_API_KEY` | `str` | API key for Groq (STT + LLM) |

### 2.2 Optional Fields with Defaults

| Env Var | Python Type | Default | Valid Values |
|---|---|---|---|
| `OPENROUTER_API_KEY` | `str` | `""` | Any OpenRouter API key string |
| `GATEKEEPER_LLM` | `str` | `"groq/llama-3.1-8b-instant"` | `provider/model` format |
| `AGENT_LLM` | `str` | `"groq/openai/gpt-oss-120b"` | `provider/model` format |
| `UTILITY_LLM` | `str` | `"groq/llama-3.3-70b-versatile"` | `provider/model` format |
| `WHISPER_MODEL_SIZE` | `str` | `"base"` | `tiny`, `base`, `small`, `medium` |
| `AUDIO_SAMPLE_RATE` | `int` | `16000` | Positive integer (Hz) |
| `AUDIO_FRAME_DURATION_MS` | `int` | `30` | `10`, `20`, or `30` (WebRTC VAD constraint) |
| `VAD_AGGRESSIVENESS` | `int` | `2` | `0`, `1`, `2`, or `3` |
| `FOLLOW_UP_TIMEOUT_SECONDS` | `float` | `30` | Positive float (seconds) |

LLM slot values use `provider/model` format. The first path segment is the provider
name (`groq` or `openrouter`); the remainder is the model ID. Parsed by
`LLMSlotConfig.parse()`.

### 2.3 Provider Selection Logic (main.py)

```
STT engine → GroqSTT (cloud Whisper-large-v3-turbo)

LLM slots (via LLMRegistry, each wrapped in LLMProxy for runtime swapping):
    "gatekeeper" → ConfigurableLLMFactory.create(GATEKEEPER_LLM)
    "agent"      → ConfigurableLLMFactory.create(AGENT_LLM)
    "utility"    → ConfigurableLLMFactory.create(UTILITY_LLM)

Supported providers: "groq" (GroqLLM), "openrouter" (OpenRouterLLM)
```

---

## 3. Audio Capture Specification

**Source:** `tusk/core/audio_capture.py`

- **Library:** `sounddevice.RawInputStream`
- **Channels:** 1 (mono)
- **Sample format:** `int16`
- **Sample rate:** `config.audio_sample_rate` (default 16000 Hz)
- **Frame size:** `config.audio_sample_rate * config.audio_frame_duration_ms // 1000` samples
- **Output:** Iterator of `bytes` objects, one per frame

---

## 4. Voice Activity Detection Specification

**Source:** `tusk/core/utterance_detector.py`

- **Library:** `webrtcvad.Vad`
- **Aggressiveness:** `config.vad_aggressiveness` (0 = least, 3 = most aggressive)

### 4.1 Utterance Boundary Logic

```
Constants:
    _SILENCE_FRAMES_THRESHOLD = 20   # consecutive unvoiced frames → end of utterance
    _MIN_VOICED_FRAMES = 5           # minimum voiced frames → valid utterance

Transition to yield:
    silence_counter >= _SILENCE_FRAMES_THRESHOLD
    AND len(voiced_frames) >= _MIN_VOICED_FRAMES
    → yield Utterance(text="", audio_frames=concat(voiced_frames), duration)
    → reset state
```

**Output:** `Iterator[Utterance]` with `text=""`, `audio_frames` set, `confidence=1.0`

---

## 5. STT Engine Specification

**Interface:** `tusk/interfaces/stt_engine.py`

```python
def transcribe(self, audio_frames: bytes, sample_rate: int) -> Utterance
```

### 5.1 WhisperSTT — `tusk/providers/whisper_stt.py`

- **Model loading:** `whisper.load_model(model_size)` at `__init__` time
- **PCM decoding:** `numpy.frombuffer(audio_frames, dtype=numpy.int16) / 32768.0`
- **Inference call:** `model.transcribe(audio, fp16=False, language="en")`
- **Confidence:** mean of `(avg_logprob + 1.0) * (1 - no_speech_prob)` per segment

### 5.2 GroqSTT — `tusk/providers/groq_stt.py`

- **Model:** `whisper-large-v3-turbo`
- **Audio format:** PCM wrapped in WAV container via `wave` stdlib
- **Hallucination detection:** regex `^\[.+\]$`; if matched → confidence `0.0`
- **Normal result:** confidence `1.0`

**Confidence gate in Pipeline:** Utterances with `confidence < 0.01` are discarded
before reaching the pipeline mode.

---

## 6. Gatekeeper Specification

**Interface:** `tusk/interfaces/gatekeeper.py`

```python
def evaluate(self, utterance: Utterance, system_prompt: str) -> GateResult
```

The `system_prompt` is provided by the current `PipelineMode`, allowing the gatekeeper
to serve different purposes in different modes without being modified.

### 6.1 GnomeGatekeeper — `tusk/gnome/gnome_gatekeeper.py`

**LLM call:** `llm_provider.complete(system_prompt, utterance.text)`

**Response parsing (robust):**

1. Strip markdown code fences
2. Parse JSON
3. If parsed value is a list, use `list[0]`
4. If parsed value has an `"arguments"` key, unwrap it
5. Extract all keys starting with `metadata_` into `GateResult.metadata`
6. On any parse failure: return `GateResult(is_directed_at_tusk=False, confidence=0.0)`

**Output:** `GateResult(is_directed_at_tusk, cleaned_command, confidence=1.0, metadata)`

### 6.2 GateResult Schema

| Field | Type | Description |
|---|---|---|
| `is_directed_at_tusk` | `bool` | Whether to process this utterance |
| `cleaned_command` | `str` | Utterance text after wake-word removal |
| `confidence` | `float` | Gatekeeper confidence |
| `metadata` | `dict[str, str]` | Mode-specific signals from the LLM response |

The `metadata` field is used by `DictationMode` to detect stop commands via
`metadata["metadata_stop"] == "true"`.

### 6.3 Conversation-Aware Gatekeeper Prompt

In command mode, the gatekeeper prompt is built dynamically by `CommandMode`.

**When outside the follow-up window** (no recent interaction or timeout expired):
The gatekeeper receives the standard static prompt — wake-word or imperative command
detection only. Behavior is identical to a stateless gatekeeper.

**When within the follow-up window** (within `FOLLOW_UP_TIMEOUT_SECONDS` of last command):
The gatekeeper prompt is extended with recent conversation context (last 6 messages,
each truncated to 150 characters). The addendum instructs the gatekeeper to treat
contextual follow-ups as directed at TUSK even without a wake word.

**Time decay:** The follow-up window starts when `CommandMode` records a successful
interaction via `InteractionClock.record_interaction()`. It expires after the
configured timeout (default 30 seconds). This prevents stale conversation context
from causing false positives on ambient speech.

**Latency impact:** No additional LLM calls. Context is formatted via string
operations (< 1 ms). The gatekeeper prompt grows by ~200-400 tokens when context
is included, adding ~10-30 ms to inference on a fast model.

---

## 7. Agent Tool Specification

**Interface:** `tusk/interfaces/agent_tool.py`

```python
@property def name(self) -> str
@property def description(self) -> str
@property def parameters_schema(self) -> dict[str, str]  # param_name → description
def execute(self, parameters: dict[str, str]) -> ToolResult
```

### 7.1 ToolRegistry — `tusk/core/tool_registry.py`

- `register(tool)` — stores tool by `tool.name`
- `get(name)` — retrieves tool by name
- `build_schema_text()` — generates LLM-readable JSON schema for all tools

`build_schema_text()` output format (one JSON line per tool):

```json
{"tool": "launch_application", "application_name": "<exec_cmd>"}
{"tool": "close_window", "window_title": "<title>"}
{"tool": "start_dictation"}
```

### 7.2 Tool Factory — `tusk/gnome/tool_factory.py`

`build_tool_registry()` creates a `ToolRegistry` and registers all 19 tools,
injecting dependencies (InputSimulator, ClipboardProvider, utility LLM, LLMRegistry).

### 7.3 Tool Catalog (19 tools)

**Application & Window Management:**

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `LaunchApplicationTool` | `launch_application` | `application_name` | Unix socket to host launcher |
| `CloseWindowTool` | `close_window` | `window_title` | `wmctrl -c` |
| `FocusWindowTool` | `focus_window` | `window_title` | `wmctrl -a` |
| `MaximizeWindowTool` | `maximize_window` | `window_title` | `wmctrl` add maximized |
| `MinimizeWindowTool` | `minimize_window` | `window_title` | `xdotool` minimize |
| `MoveResizeWindowTool` | `move_resize_window` | `window_title`, `geometry` | `wmctrl -e` |
| `SwitchWorkspaceTool` | `switch_workspace` | `workspace_number` | `wmctrl -s` |

**Input Simulation:**

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `PressKeysTool` | `press_keys` | `keys` | `InputSimulator.press_keys()` |
| `TypeTextTool` | `type_text` | `text` | `InputSimulator.type_text()` |

**Mouse Control:**

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `MouseClickTool` | `mouse_click` | `x`, `y`, `button`, `clicks` | `InputSimulator.mouse_click()` |
| `MouseMoveTool` | `mouse_move` | `x`, `y` | `InputSimulator.mouse_move()` |
| `MouseDragTool` | `mouse_drag` | `from_x`, `from_y`, `to_x`, `to_y` | `InputSimulator.mouse_drag()` |
| `MouseScrollTool` | `mouse_scroll` | `direction`, `clicks` | `InputSimulator.mouse_scroll()` |

**Clipboard:**

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `ReadClipboardTool` | `read_clipboard` | *(none)* | `ClipboardProvider.read()` |
| `WriteClipboardTool` | `write_clipboard` | `text` | `ClipboardProvider.write()` |

**Desktop Navigation:**

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `OpenUriTool` | `open_uri` | `uri` | `xdg-open` |

**Special Modes & System:**

| Tool | Name | Parameters | Execution |
|---|---|---|---|
| `DictationTool` | `start_dictation` | *(none)* | Switches pipeline to `DictationMode` |
| `AiTransformTool` | `ai_transform` | `instruction` | Copy selection → LLM transform → replace |
| `SwitchModelTool` | `switch_model` | `slot`, `provider`, `model` | `LLMRegistry.swap()` |

---

## 8. Main Agent Specification

**Source:** `tusk/core/agent.py`

```python
def process_command(self, command: str) -> None
```

### 8.1 System Prompt

Built dynamically at call time from `ToolRegistry.build_schema_text()`:

```
You are TUSK, a desktop voice assistant. Given a user command and desktop context,
call tools one at a time to complete it. Available tools:
<tool schema lines>
Respond with JSON matching one tool schema per message. On your first response you
may include an optional "reply" field with a brief acknowledgment.
Use {"tool":"done","reply":"<confirmation>"} when the task is fully complete.
Use {"tool":"unknown","reason":"<why>"} only if the command cannot be mapped.
Respond with JSON only.
```

### 8.2 User Message Construction

```
Command: <cleaned_command>
Active window: <active_window_title>
Open windows:
  <title> [<w>x<h> at <x>,<y>]
Available apps (name → exec_cmd):
<name → exec_cmd per line>
```

### 8.3 Multi-Step Agentic Loop

The agent runs a loop (max 10 steps):

1. Calls `LLMProvider.complete_messages()` with system prompt and full
   `ConversationHistory` (including tool results from prior steps)
2. Parses response JSON — extracts `"tool"` as `tool_name`, remaining fields as
   `parameters`. Optionally pops a `"reply"` field for user acknowledgment.
3. If tool is `"done"` or `"unknown"` — stops the loop
4. Otherwise executes the tool via `ToolRegistry`, appends the `ToolResult` to
   history as a user message (`"Tool result: <message>"`), and loops
5. On JSON parse failure: returns `ToolCall("done", {})` (graceful fallback)

All messages (user commands, LLM responses, tool results) are persisted in
`ConversationHistory` for cross-command context.

---

## 9. Pipeline Mode Specification

**Interface:** `tusk/interfaces/pipeline_mode.py`

```python
@property def gatekeeper_prompt(self) -> str
def handle_utterance(self, gate_result: GateResult, utterance: Utterance, controller: PipelineController) -> None
```

### 9.1 PipelineController — `tusk/interfaces/pipeline_controller.py`

```python
def set_mode(self, mode: PipelineMode) -> None
```

Implemented by `Pipeline`. Passed to `handle_utterance` so modes and tools can
trigger mode transitions without holding a reference to the pipeline directly.

### 9.2 CommandMode — `tusk/core/command_mode.py`

**Dependencies:** `MainAgent`, `InteractionClock`, `RecentContextFormatter`, `LogPrinter`

**Gatekeeper prompt (dynamic):** Built by the `gatekeeper_prompt` property:
- Outside follow-up window: standard prompt (wake word or imperative detection)
- Within follow-up window: standard prompt + follow-up addendum with recent context

Expected LLM response: `{"directed": bool, "cleaned_command": str}`.

**handle_utterance:**

1. If `gate_result.is_directed_at_tusk` is False: return (discard utterance)
2. Call `agent.process_command(gate_result.cleaned_command)`
3. Call `interaction_clock.record_interaction()` to mark the interaction time

### 9.3 DictationMode — `tusk/core/dictation_mode.py`

**Gatekeeper prompt:** Instructs LLM to detect stop-dictation commands only.
Handles STT errors ("task" for "tusk", extra commas, varied phrasing).

Expected LLM responses:
- Stop detected: `{"directed": true, "cleaned_command": "", "metadata_stop": "true"}`
- Not a stop: `{"directed": false, "cleaned_command": "<transcribed text verbatim>"}`

**Internal state:**
- `_raw_buffer: list[str]` — accumulated raw utterances
- `_pasted_char_count: int` — total characters currently in the text field from us

**handle_utterance (not a stop command):**

1. Compute `paste_text = " " + text` if buffer non-empty, else `text`
2. `text_paster.paste(paste_text)` — text appears immediately
3. Append `text` to `_raw_buffer`; increment `_pasted_char_count`
4. Send full buffer joined by spaces to LLM for cleanup
5. `text_paster.replace(_pasted_char_count, cleaned_text)` — polish in place
6. Update `_pasted_char_count = len(cleaned_text)`

**Cleanup LLM prompt:** "Clean up this dictated text. Remove filler words
(um, uh, oh, ah, like). Fix punctuation and capitalize sentences. Keep the meaning
identical. Return ONLY the cleaned text, no explanation."

**handle_utterance (stop command):**

1. If buffer non-empty: run one final cleanup + replace cycle
2. `controller.set_mode(command_mode_factory())` — return to command mode

**Latency note:** Raw text appears within ~1 second of each natural pause (VAD
silence threshold). Cleanup replaces in-place asynchronously within the same
utterance processing cycle.

---

## 10. TextPaster Specification

**Interface:** `tusk/interfaces/text_paster.py`

```python
def paste(self, text: str) -> None
def replace(self, char_count: int, new_text: str) -> None
```

### 10.1 GnomeTextPaster — `tusk/gnome/gnome_text_paster.py`

**paste:** `xdotool type --delay 0 -- <text>`

**replace:**
1. `xdotool key --delay 0 BackSpace BackSpace ...` (`char_count` BackSpace tokens)
2. `paste(new_text)`

**External dependency:** `xdotool` must be installed on the host.

---

## 11. Pipeline Specification

**Source:** `tusk/core/pipeline.py`

Implements `PipelineController`. Holds a `_current_mode: PipelineMode`.

### 11.1 Run Loop

```python
for utterance in utterance_detector.stream_utterances():
    try:
        transcribed = stt_engine.transcribe(utterance.audio_frames, sample_rate)
        if transcribed.confidence < 0.01:
            continue  # discard low-confidence
        prompt = self._current_mode.gatekeeper_prompt
        gate_result = gatekeeper.evaluate(transcribed, prompt)
        self._current_mode.handle_utterance(gate_result, self)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        continue
```

All exceptions within a single utterance cycle are caught; the loop continues.

### 11.2 set_mode

```python
def set_mode(self, mode: PipelineMode) -> None:
    self._current_mode = mode
```

Takes effect immediately on the next utterance.

---

## 12. LLM Provider Specification

**Interface:** `tusk/interfaces/llm_provider.py`

```python
@property def label(self) -> str
def complete(self, system_prompt: str, user_message: str, max_tokens: int = 256) -> str
def complete_messages(self, system_prompt: str, messages: list[dict]) -> str
```

`label` returns a human-readable identifier (e.g. `"groq/llama-3.1-8b-instant"`).
`complete_messages` supports multi-turn conversation for the agent loop.

Both providers format single-turn calls as:
`[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]`
with default `max_tokens=256`.

**Factory:** `tusk/interfaces/llm_provider_factory.py`

```python
def create(self, provider_name: str, model: str) -> LLMProvider
```

Implemented by `ConfigurableLLMFactory` which supports `"groq"` and `"openrouter"`.

**Runtime swapping:** `LLMProxy` wraps any `LLMProvider` and exposes a `swap()`
method. `LLMRegistry` manages three named slots, each holding an `LLMProxy`.
`SwitchModelTool` calls `LLMRegistry.swap()` to hot-swap models by voice.

### 12.1 OpenRouterLLM — `tusk/providers/open_router_llm.py`

- **Base URL:** `https://openrouter.ai/api/v1`
- **Headers:** `HTTP-Referer: https://github.com/vovka/tusk`, `X-Title: TUSK`

### 12.2 GroqLLM — `tusk/providers/groq_llm.py`

- **Client:** `groq.Groq`

---

## 13. Host Launcher Daemon Specification

**Source:** `launcher/tusk_host_launcher.py`

### 13.1 Socket Setup

- **Type:** `AF_UNIX`, `SOCK_STREAM`
- **Path:** `/tmp/tusk/launch.sock`

### 13.2 Connection Handling (per connection)

1. `conn.recv(4096)` → command bytes
2. Decode UTF-8 → command string
3. `shlex.split(command)` → argument list
4. `subprocess.Popen(args)` (no wait, inherits environment)
5. `conn.sendall(b"ok\n")` on success

**Why it exists:** TUSK may run in a container without access to the desktop session.
The launcher runs on the host so spawned apps appear in the desktop.

---

## 14. Data Flow Invariants

1. **All inter-component data is immutable.** Every schema type is a frozen dataclass.

2. **Text is always present before the gatekeeper.** `UtteranceDetector` yields
   utterances with `text=""`. The pipeline fills `text` via `STTEngine.transcribe()`
   before calling any `PipelineMode`.

3. **The core never imports from `gnome/` or `providers/`.** Dependency direction:
   `core → interfaces ← gnome, providers`. `main.py` is the only place where
   concrete implementations are imported and wired together.

4. **Gatekeeper prompt is always supplied by the current mode.** The gatekeeper
   has no embedded prompt; it is stateless with respect to mode.

5. **Tools are the only place platform-specific execution logic lives.** `Pipeline`,
   `MainAgent`, and `CommandMode` are all platform-agnostic.

---

## 15. Error Handling Contracts

| Component | Exception | Behaviour |
|---|---|---|
| `AudioCapture` | `sounddevice.PortAudioError` | Propagates; crashes process |
| `WhisperSTT` | Any | Propagates to Pipeline; utterance dropped |
| `GroqSTT` | Any | Propagates to Pipeline; utterance dropped |
| `GnomeGatekeeper` | JSON parse error | Returns `GateResult(is_directed_at_tusk=False)` |
| `GnomeGatekeeper` | LLM error | Propagates to Pipeline; utterance dropped |
| `MainAgent` | JSON parse error | Falls back to `ToolCall("done", {})` |
| `MainAgent` | Unknown tool name | Returns `ToolResult(success=False)`, loop continues |
| `LaunchApplicationTool` | Socket error | Returns `ToolResult(success=False)` |
| `CloseWindowTool` | Subprocess error | `subprocess.CalledProcessError` propagates |
| `Pipeline` | Any from above | Caught, printed, loop continues |

---

## 16. Latency Budget

The target end-to-end latency from end of speech to action start is ≤ 1 second.

| Stage | Implementation | Expected Latency |
|---|---|---|
| VAD boundary detection | WebRTC VAD | Negligible (real-time) |
| STT transcription | WhisperSTT (base) | ~300–800 ms (CPU) |
| STT transcription | GroqSTT | ~200–500 ms (network + cloud) |
| Gatekeeper LLM call | GroqLLM (llama-3.1-8b) | ~100–300 ms |
| Gatekeeper LLM call | OpenRouterLLM | ~200–600 ms |
| Main agent LLM call | OpenRouterLLM | ~300–800 ms |
| Desktop context query | wmctrl + xdotool | ~20–50 ms |
| Tool execution | socket / wmctrl / xdotool | ~10–30 ms |
| Context formatting | RecentContextFormatter | < 1 ms (string ops) |

**Dictation mode additional latency:**
- Raw text paste: ~10–30 ms (xdotool type)
- LLM cleanup call: ~200–600 ms (runs after paste, refines in place)

Groq for both STT and gatekeeper provides the lowest total latency path.
