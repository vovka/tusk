# Task: Unified Agent Runtime

Last-updated: 2026-03-29

## Goal

Implement a unified loop-based agent runtime so the main conversational agent and all sub-agents
share the same abstraction. Eliminate duplicated orchestration logic across agent kinds and make
agent behavior profile-driven and configurable.

## Desired Outcome

- The conversation agent will run as a real loop-based agent, not a one-shot router.
- The planner agent will run as a loop-based agent that prepares plans and selects tools.
- The executor agent will run as a loop-based agent that performs multi-step tasks with a
  runtime-selected tool set.
- All agent kinds will use the same runtime, result contract, session persistence model, and
  delegation interface.

## Scope

- Introduce shared agent abstractions in `tusk/lib/agent`.
- Keep profile definitions and application wiring in `tusk/kernel`.
- Define predefined profiles:
  - `conversation`
  - `planner`
  - `executor`
  - `default`
- Persist every agent session append-only from the beginning of the run.
- Use one unified synchronous `run_agent` interface for sub-agent execution.
- Keep model choice and static tool ownership config-driven.

## Planned Architecture

### Shared runtime

- Add `AgentRunRequest` as the normalized input for any agent run.
- Add `AgentResult` as the normalized output for parent/child communication.
- Add `AgentRuntime` as the shared multi-step loop.
- Add `AgentOrchestrator` as the profile-aware runner, session owner, and delegation entrypoint.
- Add `AgentSessionStore` with a file-backed append-only implementation.

### Kernel integration

- Replace the current main-agent path with a thin adapter over the `conversation` profile.
- Define kernel-owned profiles in `tusk/kernel/agent_profiles.py`.
- Wire profile-specific LLM slots and the agent session store from config in `main.py`.
- Remove the old direct task-execution path from the conversation flow.

### Config support

- Add config entries for:
  - `conversation_agent_llm`
  - `planner_agent_llm`
  - `executor_agent_llm`
  - `default_agent_llm`
  - `agent_session_log_dir`
- Preserve compatibility with the current environment-variable setup through fallback behavior.

## Behavior Requirements

### Conversation profile

- Answer directly for general knowledge and non-tool conversation.
- Delegate actionable work through `run_agent`.
- Use a minimal tool set.

### Planner profile

- Plan only; do not execute tasks directly.
- Select real runtime tool names for the executor.
- Return `selected_tool_names` plus plan text in a structured payload.
- Be given the planner-selectable runtime tool names by default in prompt/context.
- Optionally inspect richer tool details through `list_available_tools`.

### Executor profile

- Run with runtime-selected real tools only.
- Receive plan/session context through `session_refs`.
- Execute multi-step desktop tasks using the shared loop runtime.
- Return a normal `AgentResult`.

## Runtime Rules

- Use `done` as the terminal model-facing tool.
- Use `run_agent` as the unified synchronous delegation interface.
- Constrain `run_agent.profile_id` to predefined profile IDs.
- Persist all sessions incrementally with append-only events.
- Do not expose raw session files to prompts; use deterministic session digests instead.

## Validation Requirements

- Reject planner outputs that do not include `selected_tool_names`.
- Validate planner-selected tool names against the actual tool registry.
- Reject planner results that contain non-tool names such as `executor` or `desktop`.
- Allow executor startup only when real runtime tools are available.
- Resolve runtime tools from planner results deterministically when possible.

## Known Risks To Address During Implementation

- Models may invent tool names or profile names if the contract is too open.
- Terminal tool naming may drift if model-facing tools are unnatural.
- Planner output may be too weak if enforced only by prompt text.
- Oversized executor prompts may cause provider failures or malformed tool calls.
- Replayed session history may pollute later turns with failed attempts or invalid tool calls.
- The conversation agent may retry failed sub-agent runs too aggressively, increasing latency.

## Follow-up Work

- Add focused runtime-native tests for planner validation, executor tool hydration, and child-failure bubbling.
- Reduce session digest noise and prompt bloat.
- Stop repeated conversation-agent retries after terminal executor failures.
- Keep executor instructions compact and avoid embedding large generated texts directly into prompts.
