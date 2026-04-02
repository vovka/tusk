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
| `PLANNER_LLM` | `LLMSlotConfig` | `groq/openai/gpt-oss-20b` | Strict-schema model for one-shot planning |
| `AGENT_LLM` | `LLMSlotConfig` | `groq/openai/gpt-oss-120b` | Capable model for conversation + execution |
| `UTILITY_LLM` | `LLMSlotConfig` | `groq/llama-3.3-70b-versatile` | Model for summaries and text cleanup |

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
    "gatekeeper" → ConfigurableLLMFactory.create(GATEKEEPER_LLM.provider_name, GATEKEEPER_LLM.model)
    "planner"    → ConfigurableLLMFactory.create(PLANNER_LLM.provider_name, PLANNER_LLM.model)
    "agent"      → ConfigurableLLMFactory.create(AGENT_LLM.provider_name, AGENT_LLM.model)
    "utility"    → ConfigurableLLMFactory.create(UTILITY_LLM.provider_name, UTILITY_LLM.model)

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

## 6. Hallucination Filter Specification

**Source:** `tusk/kernel/hallucination_filter.py`

Applied after STT, before the gatekeeper. Implements `UtteranceFilter`.

```python
def is_valid(self, utterance: Utterance) -> bool
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

**Interface:** `tusk/kernel/interfaces/gatekeeper.py`

```python
def evaluate(self, utterance: Utterance, system_prompt: str) -> GateResult
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

**Source:** `tusk/kernel/agent.py`

```python
def process_command(self, command: str) -> str
```

### 8.1 System Prompt

```
You are TUSK, a desktop assistant.
Use execute_task for requests that require actions, tools, apps, desktop control,
  typing, clipboard, or model changes.
Requests to start or stop dictation, or to switch assistant modes, are actionable
  and must use execute_task.
Use done for conversational replies that need no task execution.
Use clarify when one short question is required before acting.
Use unknown when the request cannot be handled.
execute_task returns the final task result to the user.
Call exactly one tool.
```

### 8.2 User Message Construction

```
[Prior conversation messages from SlidingWindowHistory]
{"role": "user", "content": "Command: <cleaned_command>"}
```

### 8.3 Tool Dispatch

The agent calls `complete_tool_call` with definitions for `done`, `clarify`, `unknown`,
and `execute_task`. Response handling:

| Tool | Action |
|---|---|
| `done` | Return `parameters["reply"]` directly |
| `clarify` | Return `parameters["reply"]` directly |
| `unknown` | Return `parameters["reply"]` directly |
| `execute_task` | Call `ToolRegistry.get("execute_task").execute({"task": ...})`, return `result.message` |
| Anything else | Return `"Use execute_task for actionable requests."` |

### 8.4 History Management

After each command, the command and reply are appended as `ChatMessage` objects to
`SlidingWindowHistory`. On `append`, if history exceeds `max_messages` (20):

1. Evict the oldest half of messages
2. Take the last 6 evicted messages (truncated to 120 chars each)
3. Join with `" | "` and prepend `"Previous context summary: "`
4. Insert the summary as a `user` role message at the start of remaining history

### 8.5 LLM Failure Handling

On any exception from `complete_tool_call`, `MainAgent` logs the error and returns a
human-readable failure string from `ModelFailureReplyBuilder`. The command is still
appended to history.

---

## 9. Planner Workflow

**Source:** `tusk/kernel/llm_task_planner.py`

Implements `TaskPlanner`. A single structured-output LLM request using the `planner` slot.

### 9.1 System Prompt

```
You plan TUSK task execution.
Read the task and compact tool catalog.
Return execute when you can choose a minimal sufficient tool subset.
Return clarify when the user must answer a short question before execution.
Return unknown when the task cannot be handled.
Do not include tools that are not needed for the plan.
Use strict JSON only.
```

### 9.2 User Message

Built by `TaskPlannerMessageBuilder`:

```
Task: <task text>

Available tools:
<name>: <description>
<name>: <description>
...
```

On replan (when `previous_plan` and `needed_capability` are provided):

```
Task: <task text>

Available tools:
...

Previous plan:
- <step 1>
- <step 2>

Previous selected tools: <tool1>, <tool2>
Missing capability: <needed_capability>
```

### 9.3 Structured Output Schema

```json
{
  "type": "object",
  "properties": {
    "status": {"type": "string", "enum": ["execute", "clarify", "unknown"]},
    "user_reply": {"type": "string"},
    "plan_steps": {"type": "array", "items": {"type": "string"}},
    "selected_tools": {"type": "array", "items": {"type": "string"}},
    "reason": {"type": "string"}
  },
  "required": ["status", "user_reply", "plan_steps", "selected_tools", "reason"],
  "additionalProperties": false
}
```

### 9.4 Fallback

If `complete_structured` raises a `json_validate_failed` error, the planner retries with
`complete` and an extended prompt instructing the model to return a JSON object manually.
Other exceptions are re-raised.

### 9.5 FallbackTaskPlanner

`FallbackTaskPlanner` wraps a primary and a secondary `TaskPlanner` (both `LLMTaskPlanner`
instances, using `planner` and `utility` slots respectively). If the primary raises any
exception, it logs the failure and delegates to the secondary.

---

## 10. Execution Agent Specification

**Source:** `tusk/kernel/execution_agent.py`

Implements `TaskExecutor`.

### 10.1 System Prompt

```
You execute TUSK task plans.
Use exactly one tool per response.
Use only the tools provided in this execution session.
Split long literal text into multiple gnome.type_text calls.
Keep each gnome.type_text text argument short, about 300 characters or less.
Use done when the task is complete.
Use clarify when the user must answer one short question.
Use unknown when the task cannot be handled.
Use need_tools when the provided tool subset is insufficient.
```

### 10.2 Execution Input

- Task text
- Planner step list (formatted as `Task:\n<task>\n\nPlan:\n- step\n...`)
- Native tool definitions for the selected real tools only
- Terminal pseudo-tool definitions: `done`, `clarify`, `unknown`, `need_tools`

### 10.3 AgentToolLoop — `tusk/kernel/agent_tool_loop.py`

The execution loop (max 16 steps per execution):

```
for step in range(1, _MAX_STEPS + 1):   # _MAX_STEPS = 16
    tool_call = llm.complete_tool_call(prompt, messages, tools)

    if tool_call.tool_name in terminals:
        return _terminal(tool_call)

    if repeated_tool_call_guard.repeated(tool_call):
        return TaskExecutionResult("failed", "I need a different action...")

    result = tool_call_executor.execute(tool_call, allowed_names)
    tool_loop_recorder.add_feedback(messages, tool_call.tool_name, result)

return TaskExecutionResult("failed", "I couldn't finish the task.")
```

**Repeated tool call guard:** detects exact duplicate `(tool_name, parameters)` pairs
within a single execution. Returns failure immediately to prevent infinite loops.

**ToolLoopRecorder:** appends the tool call (as assistant message) and the tool result
(as user message) to the running `messages` list so the LLM has full execution context.

### 10.4 Terminal Tool Handling

| Terminal | Returns |
|---|---|
| `done` | `TaskExecutionResult("done", parameters["reply"])` |
| `clarify` | `TaskExecutionResult("clarify", parameters["reply"])` |
| `unknown` | `TaskExecutionResult("unknown", parameters["reply"])` |
| `need_tools` | `TaskExecutionResult("need_tools", "", reason, needed_capability)` |

### 10.5 LLM Failure in Loop

On any exception from `complete_tool_call`, the loop returns
`ToolCall("unknown", {"reply": <failure message>})` and terminates on that step.

---

## 11. Task Orchestration Specification

**Source:** `tusk/kernel/task_execution_service.py`

### 11.1 Run Loop

```python
_MAX_REPLANS = 2

def run(task):
    try:
        return _run(task, previous_plan=None, needed_capability="")
    except Exception as exc:
        return TaskExecutionResult("failed", failure_message(exc))

def _run(task, previous_plan, needed_capability):
    for attempt in range(_MAX_REPLANS + 1):
        plan = planner.plan(task, registry.build_planner_catalog_text(),
                            previous_plan, needed_capability)
        invalid = validator.validate(plan)
        if invalid:
            return TaskExecutionResult("failed", "I couldn't build a reliable plan.", invalid)
        if plan.status != "execute":
            return TaskExecutionResult(plan.status, plan.user_reply, plan.reason)
        result = executor.execute(task, plan)
        if result.status != "need_tools":
            return result
        previous_plan, needed_capability = plan, result.needed_capability
    return TaskExecutionResult("failed", "I couldn't finish the task with the available tools.",
                               "replan limit reached")
```

### 11.2 TaskPlanValidator

Validation rules applied before execution:

| Rule | Condition | Failure message |
|---|---|---|
| Execute needs steps | `status="execute"` and `plan_steps` is empty | plan invalid |
| Execute needs tools | `status="execute"` and `selected_tools` is empty | plan invalid |
| Clarify needs reply | `status="clarify"` and `user_reply` is empty | plan invalid |
| Unknown needs reply | `status="unknown"` and `user_reply` is empty | plan invalid |
| Tools must exist | any `selected_tools` entry not in `planner_tool_names()` | plan invalid |

---

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
    source: str            # "kernel" or adapter name (e.g. "gnome")
    planner_visible: bool  # default True
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
| `build_planner_catalog_text()` | `→ str` | `"name: description\n..."` (one line per tool) |
| `definitions_for(names)` | `→ list[dict]` | Full native tool defs for a named subset, sorted |

### 12.3 Planner Catalog Text Format

`build_planner_catalog_text()` returns a string in the format:
```
gnome.close_window: Close a window
gnome.focus_window: Focus a window
gnome.launch_application: Launch an application
...
start_dictation: Start adapter-driven dictation mode
switch_model: Switch LLM provider/model for a slot
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

## 13. Pipeline Specification

**Source:** `tusk/kernel/pipeline.py`

### 13.1 process_audio Run Loop

```python
def process_audio(self, audio: bytes, sample_rate: int) -> KernelResponse:
    utterance = stt_engine.transcribe(audio, sample_rate)
    log_utterance(utterance)

    if utterance.confidence < 0.01:
        return KernelResponse(False, "")       # STT hallucination, discard

    if dictation_mode is not None:             # dictation active
        return _process_dictation_utterance(utterance)

    if not utterance_filter.is_valid(utterance):
        log "filtered utterance"
        return KernelResponse(False, "")       # hallucination filter, discard

    return _process_command_utterance(utterance)
```

### 13.2 Command Utterance Processing

```python
def _process_command_utterance(utterance):
    gate = gatekeeper.evaluate(utterance, command_mode.gatekeeper_prompt)
    return command_mode.handle_gate_result(gate)
```

### 13.3 Dictation Utterance Processing

```python
def _process_dictation_utterance(utterance):
    gate = gatekeeper.evaluate(utterance, DICTATION_GATE_PROMPT)
    if gate.metadata.get("metadata_stop") not in (None, "", "None"):
        return dictation_mode.stop()
    if not utterance_filter.is_valid(utterance):
        return KernelResponse(False, "")
    return dictation_mode.process_text(utterance.text)
```

### 13.4 Mode Management

```python
def set_mode(self, mode: object | None) -> None:
    self._dictation_mode = mode
```

`set_mode(None)` returns to normal command mode. Called by `DictationRouter.stop()`.

### 13.5 process_text_command

```python
def process_text_command(self, text: str) -> KernelResponse:
    return command_mode.process_command(text)
```

Bypasses STT, hallucination filter, and gatekeeper entirely.

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
def start(self, api: object) -> None:
    for utterance in detector.stream_utterances():
        if not self._running:
            return
        result = api.submit_utterance(utterance.audio_frames, config.audio_sample_rate)
        if result.reply:
            log.log("TUSK", result.reply)
```

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
| `LLMTaskPlanner` | Schema validation error | Falls back to plain `complete` |
| `LLMTaskPlanner` | Both calls fail | Raises; caught by `TaskExecutionService` |
| `FallbackTaskPlanner` | Primary fails | Logs and delegates to secondary planner |
| `TaskExecutionService` | Any | Returns `TaskExecutionResult("failed", ...)` |
| `AgentToolLoop` | LLM failure | Returns `ToolCall("unknown", ...)`, loop terminates |
| `AgentToolLoop` | Max steps (16) | Returns `TaskExecutionResult("failed", ...)` |
| `AgentToolLoop` | Repeated tool call | Returns `TaskExecutionResult("failed", ...)` |
| `MCPToolProxy` | Adapter error | Returns `ToolResult(False, error_message)` |
| `AdapterManager` | Adapter startup fails | Logs error; continues without that adapter |
| `Pipeline.process_audio` | Any from above | Caught; returns `KernelResponse(False, "")` |
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

`tusk/kernel/tool_call_parser.py` is still present only as a legacy helper. It is not
used by the native tool-calling runtime.
