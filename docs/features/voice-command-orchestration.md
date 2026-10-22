# Voice Command Orchestration

## Overview
This flow turns spoken text into either a dropped utterance, a forwarded conversation turn, or a tool-backed task executed through planner and executor agents.

## Purpose
The voice shell uses the gatekeeper to classify utterances, then routes actionable requests into the kernel agent stack. The planner produces a tool plan, and the executor either uses real tools directly or runs a compiled `execute_tool_sequence`.

## Key Files And Structure
- `shells/voice/gate/llm_gatekeeper.py` + `shells/voice/gate/llm_client.py`: structured gatekeeper call, fallback completion, recovery dispatch.
- `tusk/kernel/agent/agent_orchestrator.py`: prepares requests, runs child agents, validates planner results, resolves executor tool context.
- `tusk/kernel/agent/agent_runtime.py`: main agent loop, repeated-call guard, turn guards, finish/fail handling.
- `tusk/kernel/agent/planner/result_validator.py` (`ResultValidator`): validates `planned_steps`, normalizes tool names, promotes valid plans to sequence mode.
- `tusk/kernel/agent/planner/runtime_tool_resolver.py` (`RuntimeToolResolver`): restores planner payload into executor `runtime_tool_names`, `execution_mode`, and `sequence_plan`.
- `tusk/kernel/agent/toolset/toolset_builder.py`: exposes either runtime tools or `execute_tool_sequence` to the executor.
- `tusk/kernel/agent/runtime/call_tool.py`: the one-shot command's tools as a single `call_tool` with a compact catalogue; `AgentRuntime` unwraps it to the real tool call before guards run.
- `tusk/kernel/agent/orchestrator_tool_dispatcher.py`: routes `run_agent`, `execute_tool_sequence`, and real tools.
- `tusk/kernel/agent/tool_sequence/plan_validator.py` (`PlanValidator`): rejects non-`sequence_callable` tools in sequence mode.
- `tusk/kernel/agent/tool_sequence/executor.py` (`Executor`): executes compiled sequence plans and emits `<goal> completed`.
- `tusk/kernel/agent/runtime/transcript.py` (`Transcript`): appends tool results back into the model transcript.
- `tusk/kernel/agent/guards/conversation_delegation_guard.py` (`ConversationDelegationGuard`): forces conversation to stop after executor/default returns `done`, and limits repeated failed executor/default delegations.

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
- Token budget: a gate command (`gate_command=True`, runtime `*`) gets `done`, `run_agent` and `call_tool` whose description lists every planner-visible tool as `name(arg, opt?, enum=a|b): description` (adapter prefix dropped when unique; descriptions that only restate the name dropped). Full per-tool schemas cost ~2,100 tokens per step against Groq's ~8K/min free-tier cap; the catalogue keeps a step under ~900 (chars/4), pinned by `tests/kernel/agent/test_command_prompt_budget.py`. Executor children still get native schemas for their narrowed subset.
- Gatekeeper structured-output failures are expected to fall back to plain completion. The log line is real, but not fatal by itself.
- Planner payload must live under `done.arguments.payload`. If the model returns `execution_mode` or `planned_steps` at the top level, `runtime.ResultFactory` drops them and planner validation fails with `invalid planned_steps`.
- Executor requests always recover a `sequence_plan` from planner `planned_steps`, even when planner mode is `normal`.
- `AgentRuntime` does not validate that an LLM tool call was actually exposed in the current tool list. If the executor invents `execute_tool_sequence` in normal mode, the dispatcher still honors it.
- `OrchestratorToolDispatcher` routes `execute_tool_sequence` whenever it sees that tool name. It does not check whether the executor was actually in sequence mode.
- `tool_sequence.PlanValidator` rejects non-`sequence_callable` tools such as `gnome.launch_application`, so an invented sequence call against a normal-mode plan fails with `tool is not sequence_callable`.
- `RepeatedToolCallGuard` only stops the third identical tool call. There is no executor-specific guard that forces `done` immediately after a successful `execute_tool_sequence`.
- `runtime.Transcript` feeds raw tool result messages back into the transcript as user messages. For sequence success this becomes `<goal> completed`, which is what the executor then sees on the next turn.
- Conversation is only forced to stop after executor/default returns `done`. After executor failure, it may still improvise or re-delegate until the failure budget trips.
- Some models emit static finish/delegation tools as `functions.done`, `functions.run_agent`, or `name=functions.done`. `ToolNameNormalizer` resolves those aliases in `CallTool.unwrap`, the one point every model tool call passes before the guards and the dispatcher.
- `ToolUseFailedRecovery` now falls back to extracting `failed_generation` directly from the provider error string when the outer wrapper cannot be parsed with `ast.literal_eval`, then best-effort recovers malformed `done(...)` calls by status and summary.

## Command Queueing (CommandWorker)
- One command runs at a time. A command identical (case and whitespace normalized) to the running or pending one is dropped.
- At most one command waits: a new, different command replaces the pending one (latest wins).
- A running command is never cancelled by a new command; only the spoken interrupt stops it.

## Testing Strategy
- `tests/kernel/agent/test_sequence_agent_flow.py`: happy-path sequence execution.
- `tests/kernel/agent/planner/test_sequence_planner_validation.py`: planner validation and sequence promotion.
- `tests/kernel/agent/test_agent_runtime.py`: planner rejection, child bubbling, executor-done conversation guard.
- `tests/kernel/agent/guards/test_executor_clipboard_guard.py`: clipboard sequencing constraints.
- `tests/shells/voice/gate/test_llm_gatekeeper.py`: structured-output fallback in the gatekeeper.

## Known Issues Or Future Improvements
- Add post-LLM validation so tool calls must be in the currently exposed tool set.
- Ignore or clear `sequence_plan` on executor requests when planner mode is `normal`.
- Add an executor guard that requires `done` immediately after successful `execute_tool_sequence`.
- Tighten planner/tool-call schema enforcement so malformed `done.arguments` cannot bypass the declared planner schema.

---
Last updated: 2026-10-01
