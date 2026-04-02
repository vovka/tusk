# Agent Profile Delegation

## Overview
TUSK agent delegation is controlled by agent profiles and the toolset builder. Profiles do not
currently have a dedicated "may delegate" or "allowed child profiles" field.

## Purpose
This note captures how `run_agent` is exposed today and what would need to change to make
delegation restrictions configurable per profile.

## Key Files And Structure
- `tusk/lib/agent/agent_profile.py`
- `tusk/kernel/agent_profiles.py`
- `tusk/lib/agent/agent_toolset_builder.py`
- `tusk/lib/agent/agent_orchestrator.py`
- `tusk/lib/agent/agent_run_guard.py`
- `tusk/lib/agent/agent_child_runner.py`

## Core Concepts
- `AgentProfile.static_tool_names` decides whether a profile sees the `run_agent` tool at all.
- `AgentToolsetBuilder` adds `run_agent` only when `"run_agent"` is present in `static_tool_names`.
- The `run_agent` schema is global today. Any profile that sees the tool can request
  `planner`, `executor`, or `default`.
- `AgentRunGuard` blocks self-recursion and excessive depth, but does not enforce
  parent-specific child-profile allowlists.

## How It Works
1. `build_agent_profiles()` creates four profiles: `conversation`, `planner`, `executor`, `default`.
2. The conversation and default profiles include `"run_agent"` in `static_tool_names`.
3. The planner profile does not include `"run_agent"`, so it cannot delegate.
4. The executor profile does not include `"run_agent"`, so it cannot delegate.
5. When a profile has `run_agent`, `AgentToolsetBuilder` exposes a function schema with a global
   `profile_id` enum of `planner`, `executor`, and `default`.
6. `AgentOrchestrator._run_agent()` accepts the child request and relies on `AgentRunGuard` to
   stop recursion or over-delegation depth.

## Important Patterns And Pitfalls
- Planner is already locked down by profile configuration.
- Executor is locked down by omitting `"run_agent"` from its profile.
- There is no current way to say "this profile may delegate, but only to planner" or similar.
- The recursion guard prevents `executor -> executor`, but not all cross-profile delegation.

## Integration Points
- Prompt guidance in `tusk/kernel/agent_profiles.py` should stay aligned with the tools a profile
  actually receives.
- Any future child-profile restriction should be enforced both in the generated tool schema and in
  orchestrator validation.

## Configuration
Current profile-level delegation control:
- All delegation forbidden: omit `"run_agent"` from `static_tool_names`.
- Delegation allowed: include `"run_agent"` in `static_tool_names`.

Suggested future profile-level control:
- Add `allowed_child_profile_ids: tuple[str, ...] = ()` to `AgentProfile`.
- Generate the `run_agent` schema enum from that allowlist.
- Reject disallowed child profiles in `AgentOrchestrator` or `AgentRunGuard`.

## Testing Strategy
- Assert which profiles expose `run_agent`.
- Assert executor cannot delegate when `run_agent` is removed.
- Assert a parent profile cannot request a child profile outside its allowlist.
- Keep recursion and max-depth tests alongside allowlist tests.

## Known Issues Or Future Improvements
- The current `_RUN_AGENT` schema is global rather than profile-specific.
- Delegation policy is partly encoded in prompts and partly in tool exposure.
- A dedicated profile allowlist would make the system safer and easier to reason about.

---
Last updated: 2026-03-29
