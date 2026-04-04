# TUSK — Technical Specification

This document describes the implemented system as it exists in code. It is a precise,
component-by-component specification derived from the actual implementation.

---

## 1. System Boundaries

TUSK runs as a Python process (optionally inside Docker). It interacts with:

- **Microphone** — via `sounddevice` in the voice shell (reads from default input device)
- **LLM APIs** — via HTTPS to Groq and/or OpenRouter
- **MCP adapters** — via stdio JSON-RPC to adapter subprocesses
- **Desktop environment** — exclusively through adapters (`adapters/gnome`), never via
  direct subprocess calls from the kernel

The voice shell owns audio capture. The kernel owns orchestration. Desktop control and
dictation are fully delegated to MCP adapters.

---

## 2. Configuration Specification

**Source:** `tusk/shared/config/config.py` and `tusk/shared/config/config_factory.py`.

All values are read from environment variables at startup. The `Config` object is
immutable (`frozen=True`) for the lifetime of the process.

### 2.1 Required Fields

| Env Var | Python Type | Description |
|---|---|---|
| `GROQ_API_KEY` | `str` | API key for Groq (STT + LLM) |

### 2.2 LLM Slots

| Env Var | Python Type | Default | Description |
|---|---|---|---|
| `GATEKEEPER_LLM` | `LLMSlotConfig` | `groq/llama-3.1-8b-instant` | Fast model for intent filtering |
| `CONVERSATION_AGENT_LLM` | `LLMSlotConfig` | falls back to `AGENT_LLM` | Conversation profile model |
| `PLANNER_AGENT_LLM` | `LLMSlotConfig` | falls back to `PLANNER_LLM` | Planner profile model |
| `EXECUTOR_AGENT_LLM` | `LLMSlotConfig` | falls back to `AGENT_LLM` | Executor profile model |
| `DEFAULT_AGENT_LLM` | `LLMSlotConfig` | falls back to `AGENT_LLM` | Default profile model |
| `UTILITY_LLM` | `LLMSlotConfig` | `groq/llama-3.3-70b-versatile` | Model for summaries and text cleanup |

Legacy fallback env vars (used when per-agent vars are absent):

| Env Var | Default | Fallback for |
|---|---|---|
| `PLANNER_LLM` | `groq/openai/gpt-oss-20b` | `PLANNER_AGENT_LLM` |
| `AGENT_LLM` | `groq/openai/gpt-oss-120b` | `CONVERSATION_AGENT_LLM`, `EXECUTOR_AGENT_LLM`, `DEFAULT_AGENT_LLM` |

### 2.3 Optional Fields with Defaults

| Env Var | Python Type | Default | Valid Values |
|---|---|---|---|
| `OPENROUTER_API_KEY` | `str` | `""` | Any OpenRouter API key string |
| `WHISPER_MODEL_SIZE` | `str` | `"base"` | `tiny`, `base`, `small`, `medium` |
| `AUDIO_SAMPLE_RATE` | `int` | `16000` | Positive integer (Hz) |
| `AUDIO_FRAME_DURATION_MS` | `int` | `30` | `10`, `20`, or `30` (WebRTC VAD constraint) |
| `VAD_AGGRESSIVENESS` | `int` | `2` | `0`, `1`, `2`, or `3` |
| `FOLLOW_UP_TIMEOUT_SECONDS` | `float` | `30` | Positive float (seconds) |
| `MAX_FOLLOW_UP_TIMEOUT_SECONDS` | `float` | `120` | Positive float (seconds); follow-up window ceiling |
| `TUSK_SHELLS` | `list[str]` | `["voice"]` | Comma-separated: `voice`, `cli` |
| `TUSK_ADAPTER_ENV_CACHE_DIR` | `str` | `".tusk_runtime/adapters"` | Directory for managed adapter venvs |
| `TUSK_CONVERSATION_LOG_DIR` | `str` | `".tusk_runtime/conversations"` | Directory for daily conversation logs (parsed but not active) |

### 2.4 LLM Slot Format and Provider Selection

LLM slot values use `provider/model` format. The first path segment is the provider
name; the remainder is the model ID. Parsed by `LLMSlotConfig.parse()`.

```
Provider selection in main.py:
    "gatekeeper"        → GATEKEEPER_LLM
    "conversation_agent" → CONVERSATION_AGENT_LLM (fallback: AGENT_LLM)
    "planner_agent"     → PLANNER_AGENT_LLM (fallback: PLANNER_LLM)
    "executor_agent"    → EXECUTOR_AGENT_LLM (fallback: AGENT_LLM)
    "default_agent"     → DEFAULT_AGENT_LLM (fallback: AGENT_LLM)
    "utility"           → UTILITY_LLM

Supported providers: "groq" (GroqLLM), "openrouter" (OpenRouterLLM)

Each slot is wrapped in LLMProxy for retry, wait indicator, and runtime swap.
```

---

## 3. Audio Capture Specification

**Source:** `shells/voice/audio_capture.py`

- **Library:** `sounddevice.RawInputStream`
- **Channels:** 1 (mono)
- **Sample format:** `int16`
- **Sample rate:** `config.audio_sample_rate` (default 16000 Hz)
- **Frame size:** `int(sample_rate * frame_duration_ms / 1000)` samples
- **Output:** `Iterator[bytes]`, one frame per iteration

---

## 4. Voice Activity Detection Specification

**Source:** `shells/voice/utterance_detector.py`

- **Library:** `webrtcvad.Vad`
- **Aggressiveness:** `config.vad_aggressiveness` (0 = least aggressive, 3 = most)

### 4.1 Utterance Boundary Logic

```
Constants:
    _SILENCE_FRAMES_THRESHOLD = 20   # consecutive silent frames → end of utterance
    _MIN_VOICED_FRAMES = 5           # minimum voiced frames → valid utterance

On each audio frame:
    is_speech = vad.is_speech(frame, sample_rate)

    if is_speech:
        append frame to voiced_frames
        reset silence_count to 0

    elif voiced_frames:
        increment silence_count
        if silence_count >= _SILENCE_FRAMES_THRESHOLD:
            if len(voiced_frames) >= _MIN_VOICED_FRAMES:
                yield Utterance(text="", audio_frames=concat(voiced_frames), duration=len*0.030)
            else:
                log "too short, discarded"
            reset voiced_frames and silence_count
```

**Output:** `Iterator[Utterance]` with `text=""`, `audio_frames` set, `confidence=1.0`

---

## 5. STT Engine Specification

**Interface:** `tusk/shared/stt/interfaces/stt_engine.py`

```python
def transcribe(self, audio_frames: bytes, sample_rate: int) -> Utterance
```

### 5.1 GroqSTT — `tusk/shared/stt/providers/groq_stt.py`

- **Model:** `whisper-large-v3-turbo`
- **Audio format:** PCM frames wrapped in WAV container via `wave` stdlib module
- **API call:** `groq.audio.transcriptions.create(file=("audio.wav", wav_bytes), model=..., language="en")`
- **Hallucination detection:** regex `^\[.+\]$` — e.g. `[BLANK_AUDIO]`, `[Music]`, `[Applause]`
  → if matched, sets `confidence=0.0`
- **Normal result:** `confidence=1.0`

### 5.2 WhisperSTT — `tusk/shared/stt/providers/whisper_stt.py`

- **Model loading:** `whisper.load_model(model_size)` at `__init__` time
- **PCM decoding:** `numpy.frombuffer(audio_frames, dtype=numpy.int16) / 32768.0`
- **Inference call:** `model.transcribe(audio, fp16=False, language="en")`
- **Confidence:** per-segment `min(1.0, max(0.0, avg_logprob + 1.0)) * (1.0 - no_speech_prob)`,
  averaged across all segments. Returns `0.0` if no segments.

---

## 6. Sanitizer Specification

**Source:** `shells/voice/stages/sanitizer.py`

Applied after transcription, before the buffer. Provider-agnostic hallucination and
ghost-phrase filter. Returns `None` to drop the utterance.

```python
def process(self, utterance: Utterance) -> Utterance | None
```

**Rejection conditions (any one triggers rejection):**

| Condition | Threshold |
|---|---|
| Duration too short | `utterance.duration_seconds < 0.4` |
| Punctuation only | all characters are non-alphanumeric |
| Known ghost phrase | text normalized to lowercase + trailing `.!?,` stripped matches the ghost phrase list |
| Short single word | exactly 1 word AND word length ≤ 3 |

**Ghost phrase list (subset):** `"thank you"`, `"thanks"`, `"okay"`, `"ok"`, `"um"`, `"uh"`,
`"hmm"`, `"bye"`, `"hello"`, `"hey"`, `"hi"`, `"yeah"`, `"yes"`, `"no"`, `"right"`,
`"sure"`, `"well"`, `"alright"`, `"you"`, `"so"`, `"oh"`, `"please subscribe"`,
`"like and subscribe"`, and others.

**Confidence gate in Pipeline:** After hallucination filtering, utterances with
`utterance.confidence < 0.01` are also discarded (catches GroqSTT hallucination detections).

---

## 7. Gatekeeper Specification

**Source:** `shells/voice/stages/gatekeeper.py`

**Interface:** `shells/voice/interfaces/gatekeeper.py`

```python
def evaluate(self, utterance: Utterance, recent: list[Utterance]) -> GateResult
def process(self, utterance, recent, candidates=None) -> GateDispatch
```

### 7.1 Schema Selection

The schema used for `complete_structured` is selected based on the system prompt content:

- If `"metadata_stop"` appears in the system prompt → **dictation schema**
- Otherwise → **command schema**

**Command schema:**
```json
{
  "classification": "command|conversation|ambient",
  "cleaned_text": "string",
  "reason": "string"
}
```

**Dictation schema:**
```json
{
  "directed": true|false,
  "cleaned_command": "string",
  "metadata_stop": "true|null"
}
```

### 7.2 Response Parsing

1. Strip markdown code fences if present
2. Parse JSON
3. If parsed value is a list, use `list[0]`
4. If parsed value has an `"arguments"` key, unwrap it
5. Extract `reason` — log it via `LogPrinter`
6. Extract `classification` — or derive from `directed` boolean: `True` → `"command"`, `False` → `"ambient"`
7. Extract `cleaned_text` or `cleaned_command` as the `cleaned_command` field
8. Extract all keys starting with `metadata_` into `GateResult.metadata`
9. Set `is_directed_at_tusk = classification in ("command", "conversation")`
10. On any parse failure → return `GateResult(False, "", 0.0)`

### 7.3 Fallback Chain

1. Try `llm.complete_structured(system_prompt, utterance.text, schema_name, schema, 512)`
2. On failure, log and try `llm.complete(system_prompt, utterance.text, 256)` (flexible parsing handles non-schema JSON)
3. On second failure → return `GateResult(False, "", 0.0)` — utterance silently discarded

### 7.4 Conversation-Aware Gatekeeper Prompt

In command mode, `CommandMode` builds the gatekeeper prompt dynamically:

**When outside the follow-up window** (no recent interaction or timeout expired):
Standard static prompt — wake-word or obvious imperative detection only. Behavior is
identical to a stateless gatekeeper.

**When within the follow-up window** (within effective timeout of last interaction):
The prompt is extended with the last 6 non-summary user messages from conversation history,
each truncated to 150 characters. This allows contextual follow-ups without a wake word.

**Follow-up window timeout:**

The gatekeeper tracks `_last_forwarded_at` internally. When it forwarded a message
within `follow_up_window_seconds` (default 30 s), recent context is included in the
classification prompt so conversational follow-ups work without a wake word.

**Latency impact:** No additional LLM calls. Context is formatted via string operations
(< 1 ms). The gatekeeper prompt grows by ~200–400 tokens when context is included.

---

## 8. Conversation Agent Specification

**Source:** `tusk/kernel/main_agent.py`, `tusk/kernel/agent_profiles.py`

The conversation agent runs through `AgentOrchestrator` and `AgentRuntime`. It delegates
actionable work via the `run_agent` tool to planner and executor child profiles.

### 8.1 System Prompt (conversation profile)

```
You are TUSK, a desktop assistant.
Answer general knowledge and non-tool conversation directly using done.
For actionable work, call run_agent with the planner profile first.
After the planner returns selected_tool_names, call run_agent with the executor profile,
passing the planner's selected_tool_names and session_id as session_refs.
If executor returns status=done, call done immediately.
If executor or default children fail twice, stop and call done with a failure summary.
Use done to finish with the final result.
```

### 8.2 Tools

| Tool | When used |
|---|---|
| `done` | Direct conversational reply or after sub-agents complete |
| `run_agent` | Delegate to `planner`, `executor`, or `default` profile |

### 8.3 History Management

`AgentRuntime` loads prior messages from `SessionStore` (file-based, keyed by session_id)
on each turn. `MainAgent` appends command + reply to `SlidingWindowHistory` after the
orchestrator returns — this is for local cross-turn context only and is not passed to
the LLM runtime.

### 8.4 LLM Failure Handling

On any exception from `complete_tool_call`, `AgentRuntime` builds a failure message via
`ModelFailureReplyBuilder` and synthesises a `done(status="failed")` call to terminate
the turn cleanly.

---

## 9. Planner Agent Specification

**Source:** `tusk/kernel/agent_profiles.py` (`planner` profile)

### 9.1 System Prompt

```
You are the TUSK planner agent.
Plan the task but do not execute it.
Select real runtime tool names for the executor.
Use the provided tool catalog to inspect tool schemas, required arguments,
  and sequence_callable flags.
Draft payload.planned_steps as concrete ordered tool steps with exact args.
Return payload.execution_mode as normal or sequence.
After drafting planned_steps, try to promote the plan to sequence mode when
  all steps are linear, deterministic, and every selected tool is sequence_callable.
For large text insertion tasks, prefer clipboard write and paste tools
  (gnome.write_clipboard + gnome.press_keys) over gnome.type_text.
Return done with payload containing selected_tool_names, execution_mode,
  plan_text, and planned_steps.
```

### 9.2 Tools

| Tool | When used |
|---|---|
| `done` | Return `payload={selected_tool_names, execution_mode, planned_steps, plan_text}` |

The full tool catalog is injected into the planner's prompt context by
`PlannerRequestEnricher` (via `AgentToolCatalog.prompt_text()`), not as a runtime tool.

### 9.3 Output

`done.payload` fields:

| Field | Type | Description |
|---|---|---|
| `selected_tool_names` | `list[str]` | Tool names; normalized from `planned_steps` by `PlannerResultValidator` |
| `execution_mode` | `str` | `"normal"` or `"sequence"` |
| `planned_steps` | `object` | `ToolSequencePlan`-shaped dict with `goal` and `steps` |
| `plan_text` | `str` | Human-readable plan (optional) |

`PlannerResultValidator` validates `planned_steps`, promotes `normal` → `sequence` when
all steps are `sequence_callable`, and derives `sequence_plan` from validated steps.

---

## 10. Executor Agent Specification

**Source:** `tusk/kernel/agent_profiles.py` (`executor` profile)

### 10.1 System Prompt

```
You are the TUSK executor agent.
Execute the plan using only the runtime tools provided.
Every response must be a single tool/function call.
When the tool named execute_tool_sequence is available, call it first with empty
  arguments {}.
Do not rewrite or reconstruct the compiled sequence plan in tool arguments.
After execute_tool_sequence returns success, your next response must call done.
For large text, prefer gnome.write_clipboard + gnome.press_keys over gnome.type_text.
After a successful clipboard write, do not write again until after a paste.
Use gnome.press_keys only for shortcuts, not literal text.
After the final successful action, your very next response must call done.
Do not invent tool names.
```

### 10.2 Tools — Normal Mode

`done` (required) + MCP tools resolved from the planner's `selected_tool_names` via
`PlannerRuntimeToolResolver`. The executor receives exactly the tools the planner selected.

### 10.2b Tools — Sequence Mode

`done` (required) + `execute_tool_sequence` (synthetic). No real MCP tools are exposed.
`execute_tool_sequence` takes empty arguments; the compiled plan is already attached to
the executor `AgentRunRequest` and retrieved by `OrchestratorToolDispatcher`.

### 10.3 AgentRuntime Loop

Max 16 steps (`executor` profile `max_steps=16`). Per step:
- Calls `profile.llm_provider.complete_tool_call(system_prompt, messages, tools)`
- `RepeatedToolCallGuard` aborts on duplicate identical `(tool_name, parameters)` pair
- Dispatches real tools or `execute_tool_sequence` through `OrchestratorToolDispatcher`;
  synthetic `done` terminates the run
- On LLM failure → `ModelFailureReplyBuilder` → `done(status="failed")`

---

## 11. AgentRuntime Specification

**Source:** `tusk/kernel/agent/agent_runtime.py`

Shared by all three profiles (conversation, planner, executor).

### 11.1 Session Lifecycle

1. `session_id = request.session_id or store.create_session_id()`
2. If new session: `store.start_session(session_id, profile_id, parent_session_id, ...)`
3. `RuntimeMessageHistoryBuilder` loads prior messages from store + appends `session_refs` digests
4. Appends user instruction to messages and store
5. Runs loop until `done` or max steps
6. `RuntimeResultFactory` persists final `AgentResult` to store

### 11.2 Terminal Condition

`done` is the only termination tool. Parameters:

| Key | Description |
|---|---|
| `status` | `done`, `clarify`, `unknown`, `failed`, `need_tools` |
| `summary` | Short human-readable result |
| `text` | Full reply text (optional) |
| `payload` | Structured data (planner uses `selected_tool_names`, `execution_mode`, `planned_steps`, `plan_text`) |


## 12. Tool Registry Specification

**Source:** `tusk/kernel/tool_registry.py`

### 12.1 RegisteredTool — `tusk/kernel/registered_tool.py`

```python
@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    input_schema: dict
    execute: Callable[[dict], ToolResult]
    source: str              # "kernel" or adapter name (e.g. "gnome")
    planner_visible: bool    # default True
    sequence_callable: bool  # default False — may appear in compiled sequence plans
```

### 12.2 Key Methods

| Method | Signature | Description |
|---|---|---|
| `register(tool)` | `→ None` | Reads `name`, `description`, `input_schema`, `execute`, `source`, `planner_visible` from tool object |
| `unregister_source(source)` | `→ None` | Removes all tools with matching `source` (used on adapter reload) |
| `get(name)` | `→ RegisteredTool` | Raises `KeyError` if not found |
| `real_tools()` | `→ list[RegisteredTool]` | All tools, sorted alphabetically |
| `planner_tools()` | `→ list[RegisteredTool]` | Only `planner_visible=True` entries |
| `planner_tool_names()` | `→ set[str]` | Name set of planner-visible tools |
| `definitions_for(names)` | `→ list[dict]` | Full native tool defs for a named subset, sorted |
| `sequence_tools()` | `→ list[RegisteredTool]` | Only `sequence_callable=True` tools |
| `sequence_tool_names()` | `→ set[str]` | Names of sequence-callable tools |

### 12.3 Planner Catalog Format

The planner catalog is built by `AgentToolCatalog.prompt_text()` (not `ToolRegistry`)
and injected into the planner's instruction by `PlannerRequestEnricher`. It is a JSON
string listing each planner-visible tool's `name`, `description`, `input_schema`,
`source`, and `sequence_callable` flag. Example shape:

```json
{"tools": [{"name": "gnome.close_window", "description": "...", "input_schema": {...},
            "source": "gnome", "sequence_callable": true}, ...]}
```

### 12.4 Native Tool Definition Format

`definitions_for(names)` returns a list of dicts in the format expected by
`LLMProvider.complete_tool_call`:

```json
[{
  "type": "function",
  "function": {
    "name": "gnome.launch_application",
    "description": "Launch an application",
    "parameters": {
      "type": "object",
      "properties": {"application_name": {"type": "string"}},
      "required": ["application_name"]
    }
  }
}]
```

---

## 13. Voice Pipeline Specification

**Source:** `shells/voice/pipeline.py`, `shells/voice/stages/`

The voice pipeline is a six-stage chain. Each stage either passes its result forward or
drops it. The pipeline is owned entirely by the voice shell — the kernel only sees
`kernel.submit(text)` calls.

### 13.1 Main Loop

```python
def _handle_utterance(utterance, submit):
    transcribed = transcriber.process(utterance)
    sanitized   = sanitizer.process(transcribed)      # None → drop
    if sanitized is None: return None
    buffered    = buffer.process(sanitized)            # BufferedUtterance
    recent      = buffer.recent(7)[:-1]
    candidates  = buffer.recoverable(recovery_candidate_limit, recovery_window_seconds)
    dispatch    = gatekeeper.process(buffered, recent, candidates)
    return _dispatch(dispatch, buffered.id, submit)
```

### 13.2 Dispatch

```python
def _dispatch(result, current_id, submit):
    if result.action == "drop" or result.text is None:
        buffer.mark_dropped(current_id)
        return None
    if result.action == "forward_recovered":
        buffer.mark_recovered(result.recovered_id)
        buffer.mark_consumed(current_id)
        return submit(result.text)
    buffer.mark_forwarded(current_id)
    return submit(result.text)
```

`GateDispatch.action` values: `forward_current`, `forward_recovered`,
`forward_clarification`, `drop`.

### 13.3 Gatekeeper Decision Logic

Primary call classifies the utterance as `command`, `conversation`, or `ambient`.

- **command** → `forward_current`
- **conversation + wake word** → `forward_current`
- **anything else** → triggers recovery call over recent `dropped` candidates:
  - `recover` (single candidate identified) → `forward_recovered`
  - `ambiguous` → `forward_clarification`
  - `none` → `drop`
- **ambient** → `drop`

### 13.4 CLI Path

```python
KernelAPI.submit(text)  # bypasses STT, sanitizer, buffer, and gatekeeper entirely
→ CommandMode.process_command(text)
→ MainAgent.process_command(text)
```

---

## 14. Pipeline Mode Specification

### 14.1 CommandMode — `tusk/kernel/command_mode.py`

**Dependencies:** `Agent`, `LogPrinter`

**handle(text):** Routes submitted text to the agent. The follow-up window is now
tracked internally by `LLMGatekeeper`, not by `CommandMode`.

**Base prompt excerpt:**
```
You are the gatekeeper for a voice assistant named TUSK.
Classify each utterance as command, conversation, or ambient.
Treat obvious desktop commands as command even without a wake word.
Return strict JSON only: {"classification":"command|conversation|ambient","cleaned_text":"...","reason":"..."}.
For command or conversation, remove wake words like 'tusk', 'task', 'hey tusk'.
```

**handle_gate_result:**
1. If `gate_result.is_directed_at_tusk` is False: log "discarded", return `KernelResponse(False, "")`
2. Call `agent.process_command(gate_result.cleaned_command)`
3. Call `interaction_clock.record_interaction()`
4. Return `KernelResponse(True, reply)`

### 14.2 AdapterDictationMode — `tusk/kernel/dictation_mode.py`

Active while a dictation session is running. Holds a `DictationState`.

**process_text(text):**
1. Call `DictationRouter.process(state, text)`
2. Log the result
3. Return the `KernelResponse`

**stop():**
1. Call `DictationRouter.stop(state)`
2. Log the result
3. Return the `KernelResponse`

---

## 15. Dictation Specification

### 15.1 StartDictationTool — `tusk/kernel/start_dictation_tool.py`

```
name = "start_dictation"
description = "Start adapter-driven dictation mode"
planner_visible = True
```

**execute():**
1. Call `ToolRegistry.get("dictation.start_dictation").execute({})`
2. If not found: return `ToolResult(False, "dictation adapter is not available")`
3. Build `DictationState(adapter_name="dictation", session_id=data["session_id"], desktop_source=primary_desktop_source)`
4. Call `pipeline.start_dictation(state)`
5. Return `ToolResult(True, "Dictation started.", data)`

### 15.2 DictationRouter — `tusk/kernel/dictation_router.py`

**process(state, text):**
1. Call `ToolRegistry.get("dictation.process_segment").execute({"session_id": ..., "text": text})`
2. If result has `data.operation == "insert"`: call `gnome.type_text`
3. If result has `data.operation == "replace"`: call `gnome.replace_recent_text`
4. Return `KernelResponse(True/False, message)`

**stop(state):**
1. Call `ToolRegistry.get("dictation.stop_dictation").execute({"session_id": ...})`
2. Call `pipeline.stop_dictation()` — sets `_dictation_mode = None`
3. Return `KernelResponse(True, "Dictation stopped.")`

### 15.3 DictationServer — `adapters/dictation/server.py`

MCP server managing dictation sessions.

**Tools:**

| Tool | Input | Output |
|---|---|---|
| `start_dictation` | *(none)* | `{"session_id": "<uuid>"}` in `data` |
| `process_segment` | `session_id`, `text` | Edit operation in `data`: `{"operation": "insert", "text": "...", "replace_chars": 0}` |
| `stop_dictation` | `session_id` | Success confirmation |

**Segment logic:**
- First segment of a session: output text as-is
- Subsequent segments: prepend a space unless the segment starts with punctuation
- `DictationRefiner.refine(text)` is called on each segment for LLM-based cleanup

### 15.4 DictationGate — `tusk/kernel/dictation_gate.py`

Called by `KernelAPI._submit_dictation()` before forwarding text to
`AdapterDictationMode`. Replaces the former hard-coded `_is_stop_request()` phrase list.

**should_stop(text) → bool:**
1. Call `LLMProvider.complete_structured(DICTATION_GATE_PROMPT, text, "dictation_gatekeeper", schema, 128)`
2. On failure, fall back to `LLMProvider.complete(DICTATION_GATE_PROMPT, text, 128)`
3. On second failure, return `False` (treat as dictation text)
4. Parse JSON response; extract `directed` (bool) and `metadata_stop` (str | null)
5. Return `True` only when `directed=true` AND `metadata_stop` is a non-empty string

**Structured output schema:**
```json
{
  "directed": bool,
  "cleaned_command": "string",
  "metadata_stop": "string | null"
}
```

**Prompt source:** `tusk/kernel/dictation_gate_prompt.py` (`DICTATION_GATE_PROMPT`)

---

## 16. Adapter Specification

### 16.1 Adapter Manifest Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | yes | Adapter name; prepended to all tool names |
| `transport` | `str` | yes | `"stdio"` only (HTTP not implemented) |
| `entry` | `str` | yes | Command to launch the server |
| `provides_context` | `bool` | no | Marks this adapter as the primary desktop source |

### 16.2 AdapterManager Startup

**Source:** `tusk/kernel/adapter_manager.py`

```
start_all():
    for each adapters/*/ directory:
        if adapter.json exists and transport == "stdio":
            try:
                connect_stdio(command, cwd)         # shared env startup
            except:
                env = AdapterEnvironmentBuilder.build(path, manifest)
                connect_stdio(command, cwd, env=env) # managed venv startup
            tools = client.list_tools()
            for tool in tools:
                registry.register(MCPToolProxy(adapter_name, tool, client, run_async))
            if provides_context and no context adapter yet:
                _context_adapter = adapter_name
```

**Managed environment:** `AdapterEnvironmentBuilder` discovers a `requirements.txt` in
the adapter directory and creates/reuses a virtualenv under `TUSK_ADAPTER_ENV_CACHE_DIR`.

### 16.3 MCPClient — `tusk/shared/mcp/mcp_client.py`

Synchronous stdio JSON-RPC 2.0 client.

**connect_stdio(command, cwd, env=None):**
- Spawns subprocess with `stdin=PIPE, stdout=PIPE, stderr=PIPE`
- Sends `initialize` request with `{"protocolVersion": "2024-11-05", "capabilities": {}}`

**list_tools():**
- Sends `tools/list` request
- Returns list of `MCPToolSchema` from the `"tools"` array in the response

**call_tool(name, arguments):**
- Sends `tools/call` request with `{"name": name, "arguments": arguments}`
- Returns `MCPToolResult` from the `"content"` array + `"isError"` + `"data"` fields

**Protocol format:**
```json
→ {"jsonrpc": "2.0", "id": N, "method": "tools/call", "params": {"name": "...", "arguments": {...}}}
← {"jsonrpc": "2.0", "id": N, "result": {"content": [{"type": "text", "text": "..."}], "isError": false}}
```

### 16.4 MCPToolProxy — `tusk/shared/mcp/mcp_tool_proxy.py`

Bridges `MCPToolSchema` → `RegisteredTool` interface.

- `name` → `"{adapter_name}.{schema.name}"`
- `description` → `schema.description`
- `input_schema` → `schema.input_schema`
- `source` → adapter name
- `execute(parameters)` → calls `MCPClient.call_tool(schema.name, parameters)` synchronously
  via `run_async`, converts result to `ToolResult`

---

## 17. Shell Specification

### 17.1 Shell Discovery

`main.py` reads `shells/{name}/shell.json` for each name in `config.shells`:

```json
{
  "name": "voice",
  "entry_module": "voice_shell",
  "entry_class": "VoiceShell"
}
```

The module is loaded via `importlib.util.spec_from_file_location` and the class is
instantiated. `VoiceShell` receives `(config, log)`; `CLIShell` receives no arguments.

### 17.2 VoiceShell — `shells/voice/voice_shell.py`

```python
def start(self, submit: object) -> None:
    for result in self._pipeline.run(submit):
        if not self._running:
            return
        if result.reply:
            log.log("TUSK", result.reply)
```

The pipeline handles STT, sanitization, buffering, and gatekeeper internally.
`submit` is `kernel.submit`.

### 17.3 CLIShell — `shells/cli/cli_shell.py`

```python
def start(self, api: object) -> None:
    while True:
        text = input("tusk> ")
        if text.strip().lower() in {"exit", "quit"}:
            return
        result = api.submit_text(text)
        if result.reply:
            print(result.reply)
```

### 17.4 Threading Model

```python
for shell in shells[:-1]:
    threading.Thread(target=shell.start, args=(kernel_api,), daemon=True).start()
if shells:
    shells[-1].start(kernel_api)   # last shell blocks the main thread
```

---

## 18. LLM Provider Specification

### 18.1 LLMProxy — `tusk/shared/llm/llm_proxy.py`

All LLM calls from the kernel go through `LLMProxy`.

- **Wait indicator:** `log.show_wait(label)` before call, `log.clear_wait()` in `finally`
- **Payload logging:** `LLMPayloadLogger` logs prompts and messages under the debug group
- **Retry:** `LLMRetryRunner.run(operation, on_retry)` wraps every call
- **Swap:** `swap(new_provider)` replaces `_inner` atomically; no new proxy needed

### 18.2 LLMRetryRunner — `tusk/shared/llm/llm_retry_runner.py`

```
attempts = 3
delay = 0.5 * attempt seconds (linear backoff)

Retried errors (LLMRetryPolicy.should_retry):
    HTTP 429, 500, 502, 503, 504
    "api fail", "connection", "rate limit", "service unavailable"
    "temporarily unavailable", "timeout", "timed out"

NOT retried:
    "invalid_request_error"
    "tool_use_failed"
```

### 18.3 GroqLLM — `tusk/shared/llm/providers/groq_llm.py`

- **Client:** `groq.Groq(api_key=..., timeout=30.0)`
- **complete / complete_messages:** `chat.completions.create(model, messages, max_tokens=1024)`
- **complete_tool_call:** `tool_choice="required"` first; falls back to `"auto"` if provider
  returns "did not call a tool" error
- **complete_structured:** Uses `response_format={"type": "json_schema", ...}` for strict
  schema models (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`); falls back to
  `{"type": "json_object"}` for others
- **label:** `"groq/<model>"`

### 18.4 OpenRouterLLM — `tusk/shared/llm/providers/open_router_llm.py`

- **Client:** `openai.OpenAI(base_url="https://openrouter.ai/api/v1", timeout=15.0)`
- **Headers:** `HTTP-Referer: https://github.com/vovka/tusk`, `X-Title: TUSK`
- **complete_structured:** Falls back to plain `complete` (no schema enforcement)
- **label:** `"openrouter/<model>"`

---

## 19. Data Flow Invariants

1. **All inter-component data is immutable.** Every schema type is a frozen dataclass.

2. **Text is always present before the gatekeeper.** `UtteranceDetector` yields
   utterances with `text=""`. The pipeline fills `text` via `STTEngine.transcribe()`
   before calling any gatekeeper or mode handler.

3. **`tusk.kernel` depends only on `tusk.lib` interfaces.** Concrete implementations
   are injected from `main.py`. Kernel modules never import from `tusk.lib` concrete classes.

4. **`tusk.lib` may import only `tusk.kernel.schemas`.** No business logic from kernel
   flows into infrastructure packages.

5. **Adapters are isolated processes.** The kernel has no Python import dependency on
   any adapter module. All adapter interaction is via MCP protocol.

6. **Gatekeeper prompt is always supplied by the caller.** The gatekeeper is stateless
   with respect to classification rules.

7. **Tools are the only place platform-specific execution logic lives.** `Pipeline`,
   `MainAgent`, and `CommandMode` contain no platform-specific code.

---

## 20. Error Handling Contracts

| Component | Exception | Behaviour |
|---|---|---|
| `AudioCapture` | `sounddevice.PortAudioError` | Propagates; crashes process |
| `GroqSTT` | Any | Propagates to `Transcriber`; utterance dropped |
| `WhisperSTT` | Any | Propagates to `Transcriber`; utterance dropped |
| `Sanitizer` | — | Returns `None`; utterance discarded silently |
| `LLMGatekeeper` | JSON parse error | Returns `GateResult(False, "", 0.0)` |
| `LLMGatekeeper` | Both LLM calls fail | Returns `GateResult(False, "", 0.0)` |
| `MainAgent` | LLM failure | Returns `ModelFailureReplyBuilder` string; loop continues |

| `AgentRuntime` | LLM failure | `ModelFailureReplyBuilder` → `done(status="failed")` |
| `AgentRuntime` | Max steps (8/16) | Returns `AgentResult(status="failed")` |
| `AgentRuntime` | Repeated tool call | Returns `AgentResult(status="failed")` |
| `PlannerResultValidator` | Invalid planner output | Validates `planned_steps`; promotes to sequence when eligible; fails if no valid steps |
| `PlannerStepPlanValidator` | Malformed `planned_steps` | Rejects forbidden synthetic tools, validates step structure and args |
| `ToolSequencePlanValidator` | Invalid sequence plan | Rejects non-`sequence_callable` tools, enforces max 8 steps |
| `ToolSequenceExecutor` | Step failure | Aborts remaining steps; returns partial result |
| `MCPToolProxy` | Adapter error | Returns `ToolResult(False, error_message)` |
| `AdapterManager` | Adapter startup fails | Logs error; continues without that adapter |
| `VoicePipeline._handle_utterance` | Any from above | Stage returns `None`; utterance dropped |
| `LLMRetryRunner` | Retryable error | Retries up to 3 times with linear backoff |
| `LLMRetryRunner` | Non-retryable | Re-raises immediately |

---

## 21. Latency Budget

Target end-to-end latency from end of speech to action start: ≤ 1.5 seconds.

| Stage | Implementation | Expected Latency |
|---|---|---|
| VAD boundary detection | WebRTC VAD | Negligible (real-time) |
| STT transcription | GroqSTT (Whisper-large-v3-turbo) | ~200–500 ms (network + cloud) |
| Sanitizer | `Sanitizer.process()` | < 1 ms (string ops) |
| Gatekeeper LLM call | GroqLLM (llama-3.1-8b-instant) | ~100–300 ms |
| Conversation agent LLM call | GroqLLM (gpt-oss-120b) | ~300–600 ms |
| Planner LLM call | GroqLLM (gpt-oss-20b, structured) | ~200–500 ms |
| Execution agent LLM call | GroqLLM (gpt-oss-120b) | ~300–600 ms |
| MCP tool execution | stdio JSON-RPC | ~10–50 ms |
| Context formatting | `RecentContextFormatter` | < 1 ms (string ops) |

**Total (typical path, no replan):** STT + gatekeeper + agent + planner + executor
= ~1.1–2.5 seconds. Replanning adds one additional planner + executor round.

**Dictation mode additional latency:**
- Raw text insert: ~10–30 ms (xdotool type via gnome adapter)
- LLM segment refinement: ~200–500 ms (runs in `process_segment`, refines before typing)

---

## 22. Removed Runtime Behavior

The active runtime no longer uses:

- `find_tools` — broker tool for dynamic tool discovery
- `describe_tool` — broker tool for tool schema retrieval
- `run_tool` — broker tool for indirect tool execution
- Described-tool tracking and learned top-tool injection
- Persistent tool-usage ranking
- Automatic desktop-context injection into agent prompts
- `list_available_tools` — formerly exposed to the planner profile; replaced by full
  tool catalog text injected into the planner's system prompt via `AgentToolCatalog`.
  The tool is still dispatched by `OrchestratorToolDispatcher` but no longer appears
  in any profile's toolset.
- Hard-coded `_is_stop_request()` phrase matching in `KernelAPI` — replaced by
  `DictationGate` LLM-based classification.

`tusk/kernel/tool_call_parser.py` is still present only as a legacy helper. It is not
used by the native tool-calling runtime.
