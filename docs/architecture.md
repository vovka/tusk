# TUSK — Current Architecture

## Layers

TUSK is split into three layers:

1. `tusk/kernel/`
   Owns STT, gatekeeping, conversation state, planner/executor orchestration, tool registry, and adapter lifecycle.
2. `shells/`
   User-facing entrypoints. `shells/voice` owns microphone capture and VAD. `shells/cli` is a direct text shell.
3. `adapters/`
   MCP servers discovered from `adapters/*/adapter.json`. `adapters/gnome` provides desktop-control tools. `adapters/dictation` owns dictation refinement sessions.

## Agent Structure

TUSK no longer uses a broker-style single agent.

- The **conversation agent** keeps only user-facing history and sees one operational tool: `execute_task`.
- The **planner** is a one-shot structured-output workflow. It receives the task plus a compact full tool catalog built from `name + description` only.
- The **execution agent** receives the task, the planner step list, and only the selected native tool schemas.

This keeps full tool schemas out of most requests and keeps execution chatter out of conversation history.

## Runtime Flow

### Voice shell

`AudioCapture` -> `UtteranceDetector` -> `KernelAPI.submit_utterance()` -> STT -> gatekeeper -> conversation agent -> `execute_task` -> planner -> execution agent -> MCP adapter

### CLI shell

stdin -> `KernelAPI.submit_text()` -> conversation agent -> `execute_task` -> planner -> execution agent -> MCP adapter

`submit_text()` bypasses STT and gatekeeping. It is treated as a direct command path.

## Planning And Execution

### Planner input

The planner receives:

- the normalized user task
- a compact catalog of all executable real tools
- on replan only: the previous plan, previous selected tools, and the executor's `need_tools` reason

The planner does not receive native tool definitions.
The planner slot should use a strict-schema-capable model, with a kernel fallback for older
`{"execute":[...]}` planner payloads.

### Planner output

The planner returns structured JSON with:

- `status`: `execute`, `clarify`, or `unknown`
- `user_reply`
- `plan_steps`
- `selected_tools`
- `reason`

If `status=execute`, the kernel validates the selected tool names against the real registry before execution begins.

### Executor behavior

The execution agent uses native tool calling with only:

- selected real tools
- `done`
- `clarify`
- `unknown`
- `need_tools`

If execution lacks capability, it calls `need_tools`. The kernel reruns planning with the prior plan and the requested capability. Replanning is capped to avoid runaway loops.

## Tool Model

- There is no automatic desktop-context injection into agent prompts.
- There are no runtime broker tools like `find_tools`, `describe_tool`, or `run_tool`.
- `execute_task` is a kernel-internal tool exposed only to the conversation agent.
- Real tool discovery for planning is deterministic code over `ToolRegistry`, not an LLM tool loop.
- Real tool execution still goes through the existing registry and MCP adapter path.

## Adapter Model

- Adapters are started from `adapter.json`.
- Tool names are registered as `adapter_name.tool_name`.
- The kernel uses stdio JSON-RPC for v1.
- `AdapterManager` can watch `adapters/` for hot-plug and tries shared-env startup first, then a managed env under `.tusk_runtime/adapters/` if needed.
- Desktop inspection and control tools live in adapters and are selected by the planner when needed.

## Dictation

- `start_dictation` remains a real kernel tool and is visible to the planner.
- The kernel starts a session in `adapters/dictation`.
- While dictation is active, the kernel bypasses gatekeeping and forwards transcript chunks to the dictation adapter.
- The dictation adapter returns edit operations.
- The kernel applies those edits through the active desktop adapter.

## Notes

- `tusk/kernel/tool_call_parser.py` is still present as a documented legacy helper, but it is not used by the active native tool-calling runtime.
- HTTP MCP transport is not implemented yet.
- Dangerous-action confirmation remains out of scope.
