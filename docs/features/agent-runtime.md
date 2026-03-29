# Agent Runtime

Last-updated: 2026-03-28

## Overview

TUSK now uses a shared loop-based agent runtime in `tusk/lib/agent` for all agent kinds.
The kernel defines predefined profiles (`conversation`, `planner`, `executor`, `default`),
but the runtime, session persistence, delegation, and result contract are library-level.

## Key Flow

- `MainAgent` is now a thin adapter over the `conversation` profile.
- The conversation profile answers directly when no tools are needed.
- For actionable tasks, the conversation profile delegates with `run_agent`.
- The planner profile returns `selected_tool_names` and plan text in a structured payload.
- The executor profile receives runtime-selected tools and may also receive `session_refs`.

## Key Files

- `tusk/lib/agent/agent_orchestrator.py`
- `tusk/lib/agent/agent_runtime.py`
- `tusk/lib/agent/file_agent_session_store.py`
- `tusk/kernel/agent_profiles.py`
- `tusk/kernel/agent.py`

## Contracts

- `AgentRunRequest` is the normalized input for any agent run.
- `AgentResult` is the normalized output for parent/child communication.
- `done` is the terminal tool used by every profile.
- `run_agent` is the unified synchronous delegation tool.
- `list_available_tools` exposes the planner-facing runtime tool catalog.

## Persistence

- Every agent session is stored append-only under `TUSK_AGENT_SESSION_LOG_DIR`.
- Sessions write events for start, messages, tool calls, tool results, child runs, and finish.
- `session_refs` are resolved by the runtime into deterministic digests instead of exposing raw files to prompts.

## Conventions And Pitfalls

- Dynamic runtime tools are executor-only in v1.
- Runtime-selected tools are filtered through the profile allowlist; executor uses `*` to allow requested real tools.
- Child sessions do not inherit parent message history automatically.
- Planner/executor behavior is profile-driven; avoid reintroducing separate orchestration stacks in `kernel`.

## Testing

- Direct smoke checks covered:
  - conversation direct reply
  - planner -> executor synchronous delegation
  - session-store append/read behavior
  - config fallback for profile-specific LLM slots

## Likely Next Improvements

- Replace remaining legacy planner/executor classes and tests with runtime-native coverage.
- Add richer session digest shaping for explanation-style executor tasks.
- Add async child execution only if a real workflow requires it.
