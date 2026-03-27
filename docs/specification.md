# TUSK — Technical Specification

This document describes the implemented system as it exists in code after the planner/executor refactor.

## 1. Configuration

All runtime configuration is read through `tusk/lib/config/config.py` and `tusk/lib/config/config_factory.py`.

Required:

- `GROQ_API_KEY`

LLM slots:

- `GATEKEEPER_LLM`
- `PLANNER_LLM`
- `AGENT_LLM`
- `UTILITY_LLM`

Other runtime settings:

- `OPENROUTER_API_KEY`
- `WHISPER_MODEL_SIZE`
- `AUDIO_SAMPLE_RATE`
- `AUDIO_FRAME_DURATION_MS`
- `VAD_AGGRESSIVENESS`
- `FOLLOW_UP_TIMEOUT_SECONDS`
- `MAX_FOLLOW_UP_TIMEOUT_SECONDS`
- `TUSK_SHELLS`
- `TUSK_ADAPTER_ENV_CACHE_DIR`
- `TUSK_CONVERSATION_LOG_DIR`

`TUSK_CONVERSATION_LOG_DIR` is still parsed into `Config`, but it is not part of the active planner/executor runtime path.

## 2. LLM Slots

`main.py` builds `tusk.lib.llm.LLMRegistry` with four swappable slots:

- `gatekeeper`
- `planner`
- `agent`
- `utility`

The active planner uses the `planner` slot. The conversation agent and execution agent both use the `agent` slot in v1.

## 3. User-Facing Flow

### Voice path

`VoiceShell` captures audio, detects utterances, and submits them to `KernelAPI.submit_utterance()`.

The kernel then performs:

1. STT
2. hallucination filtering
3. gatekeeping
4. command processing through the conversation agent

### CLI path

`CLIShell` sends text directly to `KernelAPI.submit_text()`, which bypasses STT and gatekeeping.

## 4. Conversation Agent

`tusk/kernel/agent.py` implements the user-facing conversation agent.

It receives:

- prior user/assistant conversation history
- the new `Command: ...` message
- native tool definitions for:
  - `done`
  - `clarify`
  - `unknown`
  - `execute_task`

It does not receive:

- desktop tool schemas
- planner catalogs
- automatic desktop context

`execute_task` is the only operational tool available to the conversation agent. If selected, the tool returns the final task result directly to the user-facing agent path.

## 5. Planner Workflow

`tusk/kernel/llm_task_planner.py` implements the planner as a single structured-output LLM request.
The planner slot should use a strict-schema-capable model. If a provider still returns the older
`{"execute":[...]}` shape, the kernel normalizes that payload into a valid `TaskPlan`.

Planner input:

- task text
- compact global tool catalog built from `ToolRegistry.planner_tools()`
- optional replan context:
  - previous plan
  - previous selected tools
  - required missing capability

The planner receives `name + description` only. It does not receive native tool definitions.

Planner output schema:

```json
{
  "status": "execute|clarify|unknown",
  "user_reply": "string",
  "plan_steps": ["string"],
  "selected_tools": ["string"],
  "reason": "string"
}
```

Planner validation rules:

- `execute` requires non-empty `plan_steps` and `selected_tools`
- `clarify` and `unknown` require non-empty `user_reply`
- every selected tool must exist in `ToolRegistry.planner_tool_names()`

Invalid planner output is converted into a graceful task failure before execution begins.

## 6. Execution Agent

`tusk/kernel/execution_agent.py` implements the task execution agent.

Execution input:

- task text
- planner step list
- native tool definitions for the selected real tools only
- terminal pseudo-tools:
  - `done`
  - `clarify`
  - `unknown`
  - `need_tools`

The execution agent does not receive:

- the full tool catalog
- broker tools
- automatic desktop context

`need_tools` schema:

```json
{
  "reason": "string",
  "needed_capability": "string"
}
```

If the execution agent emits `need_tools`, the kernel replans with the previous plan and the requested missing capability.

## 7. Task Orchestration

`tusk/kernel/task_execution_service.py` coordinates planning and execution.

Flow:

1. planner builds an initial plan
2. kernel validates the plan
3. execution agent runs with the selected subset
4. if execution returns `need_tools`, the kernel replans
5. replanning is capped at 2 additional rounds

Possible final statuses:

- `done`
- `clarify`
- `unknown`
- `failed`

## 8. Tool Registry And Tool Visibility

`tusk/kernel/tool_registry.py` stores all real tools, both internal and adapter-backed.

Important registry views:

- `real_tools()`: all registered tools
- `planner_tools()`: tools with `planner_visible=True`
- `definitions_for(names)`: native tool definitions for a selected subset
- `build_planner_catalog_text()`: compact `name: description` catalog for the planner

Special case:

- `execute_task` is registered in the same registry, but `planner_visible=False`

This keeps it callable by the conversation agent without leaking it into planner selection.

## 9. Infrastructure Packages

Infrastructure now lives under `tusk.lib`:

- `tusk.lib.logging`: `ColorLogPrinter`, `DailyFileLogger`, and logging interfaces
- `tusk.lib.config`: `Config`, `ConfigFactory`, and `StartupOptions`
- `tusk.lib.llm`: proxy, registry, retry, payload logging, tool-recovery, and provider abstractions
- `tusk.lib.stt`: STT interface and provider implementations
- `tusk.lib.mcp`: MCP client, tool proxy, adapter env builder, and adapter watcher

Shared schemas still live in `tusk.kernel.schemas`.

## 10. Adapters

Adapters remain MCP servers loaded by `AdapterManager`.

- tools are registered as `adapter_name.tool_name`
- execution calls them through `MCPToolProxy`
- adapter errors are converted into failed `ToolResult`s instead of crashing the kernel path

The active runtime still uses stdio MCP transport through `tusk.lib.mcp`.

## 11. Dictation

Dictation remains a real tool path, not a planner special case.

- `start_dictation` is registered as a real kernel tool
- the planner may choose it
- dictation state is routed through `DictationRouter` and `AdapterDictationMode`

## 12. Removed Runtime Behavior

The active runtime no longer uses:

- `find_tools`
- `describe_tool`
- `run_tool`
- described-tool tracking
- learned top-tool injection
- persistent tool-usage ranking
- automatic desktop-context injection into agent prompts

`tusk/kernel/tool_call_parser.py` is still present only as a legacy helper note. It is not used by the native tool-calling runtime.
