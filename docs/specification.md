# TUSK — Technical Specification

This document describes the implemented system as it exists in code. It is a precise,
component-by-component specification derived from the actual implementation.

---

## 1. System Boundaries

TUSK runs as a Python process (optionally inside Docker). It interacts with:

- **Microphone** — via `sounddevice` (reads from default input device)
- **LLM APIs** — via HTTPS to OpenRouter and/or Groq
- **Desktop environment** — via `wmctrl` and `xdotool` subprocesses
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
| `OPENROUTER_API_KEY` | `str` | API key for OpenRouter (required unless Groq handles all LLM calls) |

### 2.2 Optional Fields with Defaults

| Env Var | Python Type | Default | Valid Values |
|---|---|---|---|
| `GROQ_API_KEY` | `str` | `""` | Any Groq API key string |
| `GATEKEEPER_MODEL` | `str` | `"liquid/lfm-2-24b-a2b"` | Any OpenRouter model ID |
| `MAIN_AGENT_MODEL` | `str` | `"x-ai/grok-4.1-fast"` | Any OpenRouter model ID |
| `WHISPER_MODEL_SIZE` | `str` | `"base"` | `tiny`, `base`, `small`, `medium` |
| `AUDIO_SAMPLE_RATE` | `int` | `16000` | Positive integer (Hz) |
| `AUDIO_FRAME_DURATION_MS` | `int` | `30` | `10`, `20`, or `30` (WebRTC VAD constraint) |
| `VAD_AGGRESSIVENESS` | `int` | `2` | `0`, `1`, `2`, or `3` |

### 2.3 Provider Selection Logic (main.py)

The `GROQ_API_KEY` presence controls which concrete implementations are used:

```
if GROQ_API_KEY is set (non-empty):
    STT engine   → GroqSTT (cloud Whisper-large-v3-turbo)
    Gatekeeper   → GnomeGatekeeper(GroqLLM(model="llama-3.1-8b-instant"))
else:
    STT engine   → WhisperSTT(model_size=config.whisper_model_size)
    Gatekeeper   → GnomeGatekeeper(OpenRouterLLM(model=config.gatekeeper_model))

Main agent always uses:
    OpenRouterLLM(model=config.main_agent_model)
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

`AudioCapture` raises `sounddevice.PortAudioError` if the microphone is unavailable.

---

## 4. Voice Activity Detection Specification

**Source:** `tusk/core/utterance_detector.py`

- **Library:** `webrtcvad.Vad`
- **Aggressiveness:** `config.vad_aggressiveness` (0 = least, 3 = most aggressive)
- **Frame duration constraint:** Must be 10, 20, or 30 ms (WebRTC VAD requirement)

### 4.1 Utterance Boundary Logic

```
Constants:
    _SILENCE_FRAMES_THRESHOLD = 20   # consecutive unvoiced frames → end of utterance
    _MIN_VOICED_FRAMES = 5           # minimum voiced frames → valid utterance

State machine per frame:
    voiced frames list  ← accumulate voiced frames
    silence counter     ← count consecutive unvoiced frames after voice

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

Input `audio_frames` is raw int16 PCM, little-endian.
Output `Utterance` has `text` and `confidence` set; `audio_frames` is passed through.

### 5.1 WhisperSTT — `tusk/providers/whisper_stt.py`

- **Model loading:** `whisper.load_model(model_size)` at `__init__` time
- **PCM decoding:** `numpy.frombuffer(audio_frames, dtype=numpy.int16) / 32768.0`
  (float32 normalization)
- **Inference call:** `model.transcribe(audio, fp16=False, language="en")`
- **Confidence computation:**
  - For each segment: `score = exp(avg_logprob) * (1 - no_speech_prob)`
  - Final confidence: mean of segment scores (or `0.0` if no segments)
- **Output text:** Stripped result text

### 5.2 GroqSTT — `tusk/providers/groq_stt.py`

- **Model:** `whisper-large-v3-turbo`
- **Audio format:** Raw PCM is wrapped in a WAV container before submission
  (uses `wave` stdlib module, writes to `io.BytesIO`)
- **API call:** `groq.audio.transcriptions.create(file=("audio.wav", wav_bytes), model=...)`
- **Hallucination detection:** Regex `\[.*?\]` on result text; if matched → confidence `0.0`
- **Normal result:** confidence `1.0`

**Confidence gate in Pipeline:** Utterances with `confidence < 0.01` are discarded
before reaching the gatekeeper.

---

## 6. Gatekeeper Specification

**Interface:** `tusk/interfaces/gatekeeper.py`

```python
def evaluate(self, utterance: Utterance) -> GateResult
```

### 6.1 GnomeGatekeeper — `tusk/gnome/gnome_gatekeeper.py`

**System prompt instructs the LLM to:**

1. Determine if the utterance is directed at TUSK — either by:
   - Explicit mention of "tusk" or "task"
   - Clear imperative desktop command phrasing
2. Return JSON: `{"directed": bool, "cleaned_command": str}`
   where `cleaned_command` has the wake word removed.

**LLM call:** `llm_provider.complete(system_prompt, utterance.text)`

**Response parsing (robust):**

1. Strip markdown code fences (` ```json ... ``` ` or ` ``` ... ``` `)
2. Extract first `{...}` JSON object via regex
3. If parsed value is a list, use `list[0]`
4. If parsed value has an `"arguments"` key, unwrap it
5. On any parse failure: return `GateResult(is_directed_at_tusk=False, ...)`

**Wake-word stripping** (applied to `cleaned_command` after parsing):

Regex removes any of: `hey tusk`, `tusk`, `hey task`, `task` from the start of the
string (case-insensitive).

**Output:** `GateResult(is_directed_at_tusk, cleaned_command, confidence=1.0)`

**Gate in Pipeline:** Utterances where `is_directed_at_tusk is False` are discarded.

---

## 7. Context Provider Specification

**Interface:** `tusk/interfaces/context_provider.py`

```python
def get_context(self) -> DesktopContext
```

### 7.1 GnomeContextProvider — `tusk/gnome/gnome_context_provider.py`

Called once per command, immediately before the main agent LLM call.

**Window list:** `wmctrl -l` output parsed line by line.
Format: `<window_id> <desktop> <host> <title>`
Fields split on whitespace; title is everything after the third token.

**Active window:** `xdotool getactivewindow getwindowname`
Returns the title of the focused window as a single string.

**Application name resolution:** Extracted from `wmctrl` output (third whitespace field).

**Available applications:** Delegated to `AppCatalog.list_apps()`.

**External tool failure:** If `wmctrl` or `xdotool` returns a non-zero exit code,
the context provider raises `subprocess.CalledProcessError`.

### 7.2 AppCatalog — `tusk/gnome/app_catalog.py`

**Scan directories** (in order):
1. `/usr/share/applications`
2. `/usr/local/share/applications`
3. `~/.local/share/applications`

**Parsing:** Uses `configparser` to parse each `.desktop` file as INI format.
Section: `[Desktop Entry]`

**Filter rules:**
- `Type` must equal `Application`
- `NoDisplay` must not be `true`
- `Exec` field must be present

**Exec cleaning:**
1. Remove `%`-placeholder tokens via regex `%\w`
2. Split on whitespace
3. Take first token (the executable name)

**Output:** `list[AppEntry]` sorted by `name` (case-insensitive).

---

## 8. Main Agent Specification

**Source:** `tusk/core/agent.py`

```python
def process_command(self, command: str) -> SemanticAction
```

### 8.1 System Prompt

Instructs the LLM to output exactly one JSON object with `action_type` set to one of:

- `"launch_application"` with `application_name` (the `exec_cmd` from the app catalog)
- `"close_window"` with `window_title` (exact title from the window list)
- `"unknown"` with `reason` (why the command was not understood)

### 8.2 User Message Construction

```
Command: <cleaned_command>
Active window: <active_window_title>
Active application: <active_application>
Open windows: <comma-separated window titles>
Available applications: <comma-separated "name (exec_cmd)" pairs>
```

### 8.3 LLM Call

`llm_provider.complete(system_prompt, user_message)` with `max_tokens=256`.

### 8.4 Response Parsing

Parses the LLM response string as JSON. Reads `action_type` field to construct:

- `LaunchApplicationAction(action_type, application_name)`
- `CloseWindowAction(action_type, window_title)`
- `UnrecognizedAction(action_type, reason)`

On JSON parse failure or unknown `action_type`:
returns `UnrecognizedAction(reason="parse error: ...")`.

---

## 9. Action Executor Specification

**Interface:** `tusk/interfaces/action_executor.py`

```python
def execute(self, action: SemanticAction) -> None
```

### 9.1 GnomeActionExecutor — `tusk/gnome/gnome_action_executor.py`

**`LaunchApplicationAction`:**

1. Connect to Unix domain socket at `/tmp/tusk/launch.sock`
2. Send `action.application_name` encoded as UTF-8
3. Read response (up to 1024 bytes)
4. If response does not start with `"ok"`: raise `RuntimeError`

**`CloseWindowAction`:**

1. Run `wmctrl -c <action.window_title>` as a subprocess
2. Wait for completion (`subprocess.run`)

**`UnrecognizedAction`:**

Print the `reason` to stdout. No desktop action taken.

---

## 10. Host Launcher Daemon Specification

**Source:** `launcher/tusk_host_launcher.py`

### 10.1 Socket Setup

- **Type:** `AF_UNIX`, `SOCK_STREAM`
- **Path:** `/tmp/tusk/launch.sock`
- **Directory:** `/tmp/tusk/` created if absent (`exist_ok=True`)
- **Cleanup:** Socket file removed at startup if it already exists

### 10.2 Connection Handling (per connection)

1. `conn.recv(4096)` → command bytes
2. Decode UTF-8 → command string
3. `shlex.split(command)` → argument list
4. `subprocess.Popen(args)` (no wait, inherits environment)
5. `conn.sendall(b"ok\n")` on success
6. `conn.sendall(error_message.encode())` on `Exception`

### 10.3 Lifecycle

- Runs as infinite `while True` loop
- No cleanup on exit (socket file left on disk)
- Must be started before `GnomeActionExecutor` attempts connections

---

## 11. Pipeline Specification

**Source:** `tusk/core/pipeline.py`

### 11.1 Run Loop

```python
for utterance in utterance_detector.stream_utterances():
    try:
        utterance = stt_engine.transcribe(utterance.audio_frames, sample_rate)
        if utterance.confidence < 0.01:
            continue
        gate_result = gatekeeper.evaluate(utterance)
        if not gate_result.is_directed_at_tusk:
            continue
        action = main_agent.process_command(gate_result.cleaned_command)
        action_executor.execute(action)
    except Exception as e:
        print(f"Pipeline error: {e}")
        continue
```

All exceptions within a single utterance cycle are caught and logged; the loop
continues with the next utterance. This ensures a single bad LLM response or
subprocess failure does not halt the system.

---

## 12. LLM Provider Specification

**Interface:** `tusk/interfaces/llm_provider.py`

```python
def complete(self, system_prompt: str, user_message: str) -> str
```

Both providers format the call as a two-message conversation:
`[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]`

### 12.1 OpenRouterLLM — `tusk/providers/open_router_llm.py`

- **Base URL:** `https://openrouter.ai/api/v1`
- **Client:** `openai.OpenAI` with custom base URL
- **Headers added:** `HTTP-Referer: https://github.com/tusk`, `X-Title: TUSK`
- **max_tokens:** `256`
- **Returns:** `response.choices[0].message.content`

### 12.2 GroqLLM — `tusk/providers/groq_llm.py`

- **Client:** `groq.Groq`
- **max_tokens:** `256`
- **Returns:** `response.choices[0].message.content`

---

## 13. Data Flow Invariants

These invariants hold across the entire pipeline:

1. **All inter-component data is immutable.** Every schema type is a frozen dataclass.
   No component mutates data received from another.

2. **Text is always present before the gatekeeper.** `UtteranceDetector` yields
   utterances with `text=""`. The pipeline fills `text` via `STTEngine.transcribe()`
   before calling `Gatekeeper.evaluate()`.

3. **The core never imports from `gnome/` or `providers/`.** Dependency direction:
   `core → interfaces ← gnome, providers`. `main.py` is the only place where
   concrete implementations are imported and wired together.

4. **Every public function has complete type annotations.** Parameters and return
   types are always specified.

5. **No global mutable state.** `Config` is read once at startup and never modified.
   No module-level variables change at runtime.

---

## 14. Error Handling Contracts

| Component | Exception | Behaviour |
|---|---|---|
| `AudioCapture` | `sounddevice.PortAudioError` | Propagates; crashes process |
| `WhisperSTT` | Any | Propagates to Pipeline; utterance dropped |
| `GroqSTT` | Any | Propagates to Pipeline; utterance dropped |
| `GnomeGatekeeper` | JSON parse error | Returns `GateResult(is_directed_at_tusk=False)` |
| `GnomeGatekeeper` | LLM error | Propagates to Pipeline; utterance dropped |
| `MainAgent` | JSON parse error | Returns `UnrecognizedAction(reason=...)` |
| `MainAgent` | LLM error | Propagates to Pipeline; utterance dropped |
| `GnomeActionExecutor` (launch) | Socket error | `RuntimeError` propagates to Pipeline |
| `GnomeActionExecutor` (close) | Subprocess error | Propagates to Pipeline |
| `Pipeline` | Any from above | Caught, printed, loop continues |

---

## 15. Latency Budget

The target end-to-end latency from end of speech to action start is ≤ 1 second.
Approximate contribution per stage:

| Stage | Implementation | Expected Latency |
|---|---|---|
| VAD boundary detection | WebRTC VAD | Negligible (real-time) |
| STT transcription | WhisperSTT (base) | ~300–800 ms (CPU) |
| STT transcription | GroqSTT | ~200–500 ms (network + cloud) |
| Gatekeeper LLM call | GroqLLM (llama-3.1-8b) | ~100–300 ms |
| Gatekeeper LLM call | OpenRouterLLM | ~200–600 ms |
| Main agent LLM call | OpenRouterLLM | ~300–800 ms |
| Desktop context query | wmctrl + xdotool | ~20–50 ms |
| Action execution | socket / wmctrl | ~10–30 ms |

Groq for both STT and gatekeeper provides the lowest total latency path.
Local Whisper on CPU with a cloud main agent is the highest-latency path.
