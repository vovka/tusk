# Voice Command Orchestration

## Overview
This flow turns spoken text into either a dropped utterance, a forwarded conversation turn, or a tool-backed task executed through planner and executor agents.

## Purpose
The voice shell uses the gatekeeper to classify utterances, then routes actionable requests into the kernel agent stack. The planner produces a tool plan, and the executor either uses real tools directly or runs a compiled `execute_tool_sequence`.

## Key Files And Structure
- `shells/voice/stages/gatekeeper.py`: structured gatekeeper call, fallback completion, recovery dispatch.
- `tusk/kernel/agent/agent_orchestrator.py`: prepares requests, runs child agents, validates planner results, resolves executor tool context.
- `tusk/kernel/agent/agent_runtime.py`: main agent loop, repeated-call guard, turn guards, finish/fail handling.
- `tusk/kernel/agent/planner_result_validator.py`: validates `planned_steps`, normalizes tool names, promotes valid plans to sequence mode.
- `tusk/kernel/agent/planner_runtime_tool_resolver.py`: restores planner payload into executor `runtime_tool_names`, `execution_mode`, and `sequence_plan`.
- `tusk/kernel/agent/agent_toolset_builder.py`: exposes either runtime tools or `execute_tool_sequence` to the executor.
- `tusk/kernel/agent/orchestrator_tool_dispatcher.py`: routes `run_agent`, `execute_tool_sequence`, and real tools.
- `tusk/kernel/agent/tool_sequence_plan_validator.py`: rejects non-`sequence_callable` tools in sequence mode.
- `tusk/kernel/agent/tool_sequence_executor.py`: executes compiled sequence plans and emits `<goal> completed`.
- `tusk/kernel/agent/runtime_step_recorder.py`: appends tool results back into the model transcript.
- `tusk/kernel/agent/conversation_run_agent_guard.py`: forces conversation to stop after executor/default returns `done`.
- `tusk/kernel/agent/conversation_failure_budget_guard.py`: limits repeated failed executor/default delegations.

## How It Works
1. Voice input is classified by `LLMGatekeeper`. Its structured JSON now also carries an `intent` field — a terse present-continuous refrain of the request (e.g. "Opening gedit and inserting a poem") — parsed into `GateResult.intent` and forwarded on the `GateDispatch`. When `TUSK_ACK` is on, `CommandWorker` speaks this refrain before running the command (see `docs/features/spoken-acknowledgment.md`).
2. Command-like utterances are forwarded into the kernel.
3. Conversation agent delegates to planner with the tool catalog embedded in the request.
4. Planner returns `done` with `payload.selected_tool_names`, `payload.execution_mode`, and `payload.planned_steps`.
5. Planner validation either:
   - rejects malformed `planned_steps`,
   - leaves the plan in normal mode, or
   - promotes it to sequence mode and materializes `payload.sequence_plan`.
6. Executor request resolution restores planner payload from `session_refs`.
7. Executor gets either real runtime tools or only `execute_tool_sequence`, depending on `execution_mode`.

## Important Patterns And Pitfalls
- Gatekeeper structured-output failures are expected to fall back to plain completion. The log line is real, but not fatal by itself.
- Planner payload must live under `done.arguments.payload`. If the model returns `execution_mode` or `planned_steps` at the top level, `RuntimeResultFactory` drops them and planner validation fails with `invalid planned_steps`.
- Executor requests always recover a `sequence_plan` from planner `planned_steps`, even when planner mode is `normal`.
- `AgentRuntime` does not validate that an LLM tool call was actually exposed in the current tool list. If the executor invents `execute_tool_sequence` in normal mode, the dispatcher still honors it.
- `OrchestratorToolDispatcher` routes `execute_tool_sequence` whenever it sees that tool name. It does not check whether the executor was actually in sequence mode.
- `ToolSequencePlanValidator` rejects non-`sequence_callable` tools such as `gnome.launch_application`, so an invented sequence call against a normal-mode plan fails with `tool is not sequence_callable`.
- `RepeatedToolCallGuard` only stops the third identical tool call. There is no executor-specific guard that forces `done` immediately after a successful `execute_tool_sequence`.
- `RuntimeStepRecorder` feeds raw tool result messages back into the transcript as user messages. For sequence success this becomes `<goal> completed`, which is what the executor then sees on the next turn.
- Conversation is only forced to stop after executor/default returns `done`. After executor failure, it may still improvise or re-delegate until the failure budget trips.
- Some models emit static finish/delegation tools as `functions.done`, `functions.run_agent`, or `name=functions.done`. `ToolCall` now normalizes those aliases before runtime dispatch.
- `ToolUseFailedRecovery` now falls back to extracting `failed_generation` directly from the provider error string when the outer wrapper cannot be parsed with `ast.literal_eval`, then best-effort recovers malformed `done(...)` calls by status and summary.

## Testing Strategy
- `tests/test_sequence_agent_flow.py`: happy-path sequence execution.
- `tests/test_sequence_planner_validation.py`: planner validation and sequence promotion.
- `tests/test_agent_runtime.py`: planner rejection, child bubbling, executor-done conversation guard.
- `tests/test_executor_clipboard_guard.py`: clipboard sequencing constraints.
- `tests/test_guardrail_gatekeeper.py`: structured-output fallback in the gatekeeper.

## Known Issues Or Future Improvements
- Add post-LLM validation so tool calls must be in the currently exposed tool set.
- Ignore or clear `sequence_plan` on executor requests when planner mode is `normal`.
- Add an executor guard that requires `done` immediately after successful `execute_tool_sequence`.
- Tighten planner/tool-call schema enforcement so malformed `done.arguments` cannot bypass the declared planner schema.

---
Last updated: 2026-04-04
