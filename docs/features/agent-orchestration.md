# Agent Orchestration

## Overview
TUSK uses a parent conversation agent to decide whether to answer directly, plan tool use, or
delegate execution. Planner completion is intermediate. Executor completion should usually end the
turn.

## Purpose
This note captures the parent-child control flow that prevents the conversation agent from
restarting work after an executor child has already completed the task, and limits retry loops when
executor children keep failing.

## Key Files And Structure
- `tusk/kernel/agent_profiles.py`
- `tusk/lib/agent/agent_runtime.py`
- `tusk/lib/agent/agent_orchestrator.py`
- `tusk/lib/agent/agent_child_runner.py`
- `tusk/lib/agent/runtime_step_recorder.py`
- `tusk/lib/agent/conversation_run_agent_guard.py`
- `tusk/lib/agent/conversation_failure_budget_guard.py`
- `tusk/lib/agent/executor_clipboard_guard.py`
- `tusk/lib/agent/runtime_turn_guards.py`
- `tusk/lib/agent/child_result_message_builder.py`

## Core Concepts
- The conversation profile owns the turn-level decision about whether the user request is already
  satisfied.
- Planner `done` means "plan ready", not "task complete".
- Executor `done` means the delegated execution finished and the parent should normally call `done`.
- Repeated failed executor children should not trigger unlimited retries from the conversation
  agent in the same turn.
- Clipboard-based text insertion needs its own progress guard because repeated `write_clipboard`
  calls can avoid the exact-match repeated-call guard by changing the text each time.
- Child results are fed back into the parent as structured `[child-result]` assistant messages
  instead of raw JSON user messages.

## How It Works
1. The conversation prompt tells the parent to reassess completion after every child result.
2. A planner child can return `selected_tool_names` and `plan_text`, which the conversation agent
   can pass into the executor.
3. `AgentChildRunner` wraps child results into `ToolResult.data["child_result"]` with profile,
   status, session id, summary, and payload.
4. `RuntimeStepRecorder` turns that structure into a readable `[child-result]` message for the
   parent model context.
5. `ConversationRunAgentGuard` blocks the conversation profile from calling `run_agent` again after
   an `executor` or `default` child already returned `status=done`.
6. `ConversationFailureBudgetGuard` blocks further delegation after two failed `executor` or
   `default` child runs in the same conversation turn.
7. `ExecutorClipboardGuard` blocks repeated clipboard rewrites and requires progress toward
   `gnome.focus_window` or a paste shortcut after `gnome.write_clipboard`.
8. Successful `gnome.write_clipboard` results can add a `[clipboard-written]` message so the
   executor sees the exact text it already prepared on the next turn.

## Important Patterns And Pitfalls
- Do not treat all child `done` results as terminal. Planner `done` is expected before executor.
- Treat executor and default `done` as terminal for the current conversation turn.
- Treat repeated failed executor runs as terminal too. The parent should stop and report failure
  instead of retrying indefinitely.
- After `gnome.write_clipboard`, the executor should move toward focus/paste, not keep using the
  clipboard as a scratchpad for revised text.
- When clipboard text is surfaced back into the executor context, later clipboard rewrites must not
  silently change that text before paste.
- Do not feed child results back as undifferentiated user text. That obscures control flow.
- Keep prompt guidance aligned with runtime enforcement. Prompt-only fixes are too weak here.

## Integration Points
- Planner prompt should select clipboard and paste-related tools for large text insertion tasks when
  available.
- Executor prompt should prefer `gnome.write_clipboard` plus `gnome.press_keys` over repeated
  `gnome.type_text` for large literal text blocks.
- Executor prompt should treat `gnome.press_keys` as a shortcut tool only, not a literal-text or
  URL-entry tool.
- Executor prompt should refer to the literal tool named `done`, because some model failures come
  from narrating completion in plain text instead of emitting the `done` tool call.
- Session refs still use session digests, so executor can inspect planner output through the
  existing reference mechanism.

## Configuration
- Conversation and default profiles can delegate with `run_agent`.
- Planner can inspect tools but cannot delegate.
- Executor can execute runtime tools but cannot delegate.

## Testing Strategy
- Cover `planner -> executor -> done` to ensure planning still flows into execution.
- Cover the post-executor guard so a second `run_agent` call fails immediately.
- Cover the conversation retry budget so the third failed executor attempt is blocked.
- Cover the clipboard guard so `write_clipboard -> write_clipboard` fails, while
  `write_clipboard -> focus_window -> press_keys(<ctrl>v)` still works.
- Assert prompt text for completion checks and clipboard-oriented text insertion guidance.

## Known Issues Or Future Improvements
- General runtime tool results still use the older message shape unless they are child-agent
  results.
- The conversation success guard is intentionally narrow and only applies after completed
  `executor` or `default` children.
- Clipboard progress is enforced only at the executor runtime layer. It does not validate whether
  the pasted text itself is correct.

---
Last updated: 2026-03-30
