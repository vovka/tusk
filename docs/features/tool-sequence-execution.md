# Tool Sequence Execution

## Overview
TUSK can now run a small deterministic executor plan through a single synthetic tool,
`execute_tool_sequence`, instead of asking the executor LLM what to do before every step.

## Purpose
This feature reduces latency and token cost for short desktop workflows while keeping the
top-level conversation → planner → executor delegation chain intact.

## Key Files And Structure
- `tusk/kernel/agent/agent_toolset_builder.py`
- `tusk/kernel/agent/planner_result_validator.py`
- `tusk/kernel/agent/planner_runtime_tool_resolver.py`
- `tusk/kernel/agent/tool_sequence_executor.py`
- `tusk/kernel/agent/tool_sequence_plan_validator.py`
- `tusk/kernel/agent/orchestrator_tool_dispatcher.py`
- `tusk/shared/schemas/tool_sequence_plan.py`
- `tusk/shared/mcp/mcp_tool_proxy.py`

## Core Concepts
- Planner payload now always carries `planned_steps` plus `execution_mode`.
- `sequence_plan` is now a derived field materialized from `planned_steps` after validation.
- `planned_steps` are the source of truth; `selected_tool_names` are normalized from the step plan.
- Executor still exists, but in sequence mode it sees only `done` and
  `execute_tool_sequence`.
- Sequence plans are persisted in the planner session result and recovered from
  `session_refs` for the executor request.
- Only tools marked `sequence_callable` may appear in a compiled plan.
- Validation runs twice: once on planner output, then again immediately before execution.

## How It Works
1. Planner receives the full tool catalog in its initial prompt context, then returns
   `selected_tool_names`, `planned_steps`, and `execution_mode`.
2. `PlannerResultValidator` validates `planned_steps` against real tool schemas.
3. If the inspected plan is linear and every step is `sequence_callable`,
   `PlannerResultValidator` promotes `execution_mode=normal` to `execution_mode=sequence`,
   derives `sequence_plan`, and logs the promotion under `SEQPROMOTE`.
4. `PlannerRuntimeToolResolver` loads the planner result from `session_refs` and populates
   executor `runtime_tool_names`, `execution_mode`, and `sequence_plan`.
5. In sequence mode, `AgentToolsetBuilder` exposes `execute_tool_sequence` instead of the real
   runtime tools.
6. Executor calls `execute_tool_sequence` with empty arguments, because the compiled plan is
   already attached to the resolved executor request.
7. `OrchestratorToolDispatcher` ignores model-supplied step data and routes
   `execute_tool_sequence` to
   `ToolSequenceExecutor`, which validates again and runs the approved tools directly through the
   `ToolRegistry`.

## Important Patterns And Pitfalls
- Sequence mode is linear only in v1. There are no branches, loops, retries, or step-output
  references.
- `selected_tool_names` are normalized from `planned_steps`, so harmless extra planner-selected
  tools do not block execution.
- Synthetic tools such as `done`, `run_agent`, `list_available_tools`, and
  `execute_tool_sequence` are forbidden inside a sequence plan.
- Sequence eligibility is stricter than planner visibility. A tool can be selectable without being
  sequence-callable.
- `gnome.launch_application` and `gnome.open_uri` are intentionally excluded from the v1
  allowlist because their current success semantics do not guarantee that dependent UI state is
  ready for the next step.

## Integration Points
- Planner prompt in `tusk/kernel/agent_profiles.py` tells the model to use the injected tool
  catalog, always emit `planned_steps`, and try sequence promotion after drafting the concrete
  plan.
- Executor prompt in `tusk/kernel/agent_profiles.py` tells the model to call
  `execute_tool_sequence` first with empty arguments when it is present.
- `AgentToolCatalog` now exposes `sequence_callable` in the injected planner catalog text.
- MCP-backed tools participate automatically once their proxy marks them sequence-callable.

## Configuration
- Sequence eligibility is configured by `RegisteredTool.sequence_callable`.
- GNOME MCP allowlist is currently encoded in `tusk/shared/mcp/mcp_tool_proxy.py`.
- Maximum sequence length is 8 steps.

## Testing Strategy
- Validate registry metadata and planner tool catalog exposure.
- Validate planner rejection of malformed or unauthorized sequence payloads.
- Validate executor request resolution from planner session refs.
- Validate sequence-mode tool exposure for the executor.
- Validate deterministic execution success and abort-on-failure behavior.
- Validate the end-to-end conversation → planner → executor(meta-tool) flow.

## Known Issues Or Future Improvements
- There is no wait or polling primitive yet, so sequence mode is limited to already-synchronous
  tools.
- Sequence execution records internal step events, but conversation summaries still rely on the
  existing child-result format.
- Large literal text payloads can still make planner JSON fragile; reducing payload size for
  clipboard-heavy plans remains a likely next improvement.
- Step-output references and retry policies can be added later without changing the overall
  transport path.

---
Last updated: 2026-04-03
