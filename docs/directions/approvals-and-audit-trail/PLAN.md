# Plan: Approvals & Action Audit Trail

**Branch:** `feature/approvals` · **Depends on:** nothing · **Unblocks:** write tools in
[real-world-adapters](../real-world-adapters/README.md), accessibility preset in
[vertical-packaging](../vertical-packaging/README.md).

Three PR-sized milestones. A ships flag plumbing with zero behavior change; B ships the
approval turn boundary; C ships the journal. Each leaves main releasable. TDD throughout:
every step lists its failing tests first (`docker compose exec tusk pytest tests/...`).

**Fine-grained execution detail:** [PLAN-DETAILS.md](PLAN-DETAILS.md) — commit-by-commit
breakdown grounded in the current code; where its design differs from the milestone steps
below (exception-based propagation, deterministic resume, journal as a Store decorator),
the detailed plan wins.

## Milestone A — `requires_approval` plumbing (no behavior change)

### A1. Flag: manifest → registry
- **Tests:** `tests/kernel/` adapter-manager/registry cases — manifest `tools.<name>.requires_approval: true`
  lands on `RegisteredTool.requires_approval`; default `False`; kernel tools default `False`.
- **Change:** field on `tusk/kernel/tools/registered_tool.py`; flag application in
  `tusk/kernel/core/adapter_manager.py` (same path as `sequence_callable`).

### A2. Planner visibility of the flag
- **Tests:** catalog text includes a `requires approval` marker for flagged tools.
- **Change:** `tusk/kernel/agent/agent_tool_catalog.py` — one marker, mirroring the
  `sequence_callable` annotation.

### A3. Keep flagged tools out of compiled sequences
- **Tests:** `SequencePromoter` does not promote plans containing flagged tools;
  `tool_sequence/PlanValidator` rejects them pre-execution.
- **Change:** one rule in `tusk/kernel/agent/planner/sequence_promoter.py`, one in
  `tusk/kernel/agent/tool_sequence/plan_validator.py`.

No shipped adapter gets the flag yet — a demo adapter fixture under `demos/` carries a
flagged tool for tests/e2e.

## Milestone B — awaiting_approval turn boundary

### B1. Pending-approval data + result status
- **Tests:** `AgentResult(status="awaiting_approval")` round-trips with a pending call.
- **Change:** frozen `PendingApproval` dataclass (tool name, args summary, executor
  `session_id`) in `tusk/kernel/agent/pending_approval.py`; status handling in
  `agent_result.py` / `runtime/result_factory.py`.

### B2. Gate at the dispatch point
- **Tests:** executor run reaching a flagged tool does **not** execute it; persists an
  `approval_requested` session event; returns `awaiting_approval` with the pending call.
  An `approved_call` marker on the request lets exactly that call through once.
- **Change:** `ApprovalGate` in `tusk/kernel/agent/guards/approval_gate.py`, consulted in
  `AgentRuntime` before dispatch (alongside `RepeatedToolCallGuard`); event type in
  `runtime/step_recorder.py`; optional `approved_call` on `AgentRunRequest`.

### B3. Resume entry point
- **Tests:** re-running the executor profile with `session_refs=[executor_session]` +
  `approved_call` executes the pending tool and completes; decline path records a
  `approval_declined` event and does not execute.
- **Change:** resume path in `AgentOrchestrator` (reuses existing session-store history);
  `CommandMode.resume_approved(pending)` / `cancel_pending(pending)`. v1 simplification:
  the resumed executor's reply goes straight to TTS, not back through the conversation
  profile — note in the feature doc.

### B4. `ApprovalSlot` — consuming the yes/no
- **Tests:** with an armed slot, `KernelAPI.submit("yes")` resumes; "no" cancels; an
  unrelated command cancels the pending action *and* is then processed normally (no
  deadlock); a configurable timeout (`TUSK_APPROVAL_TIMEOUT_SECONDS`, default 60)
  auto-cancels.
- **Change:** new package `tusk/kernel/modes/approval/` (modes/ is at the 12-file cap —
  subpackage justified: ≥3 cohesive files): `approval_slot.py`, `approval_prompt.py`
  (yes/no schema for the gatekeeper LLM slot, `SpeechStopGate`-style), `approval_state.py`.
  `KernelAPI.submit` checks the slot before the coding/dictation `ModeSlot`s.

### B5. Voice-shell awareness
- **Tests:** gatekeeper prompt receives an awaiting-approval probe; bare "yes"/"no"
  classifies as command while pending (unit-test the prompt assembly, not the LLM).
- **Change:** probe plumbing in `shells/voice/stages/gate/` mirroring the existing
  busy/speaking probes; wiring in `ShellLoader._wire_modes`.

### B6. Spoken prompt + e2e
- **Change:** `CommandMode` speaks "«tool summary» — yes or no?" via the existing TTS path.
- **Verify:** emulator transcript in `demos/` against the flagged demo adapter: approve
  path, decline path, unrelated-command path. Run per the e2e harness notes (compare
  scenario-for-scenario against baseline — the harness has known provider flakiness).

## Milestone C — Action journal

### C1. `ActionJournal`
- **Tests:** every dispatched tool call appends one JSONL line (timestamp, tool, args
  summary, outcome, approval verdict if any); file created lazily; write failures never
  propagate (mirror `StatusReporterHub` swallowing).
- **Change:** `tusk/kernel/agent/session/action_journal.py`; recorded from
  `runtime/step_recorder.py` and `tool_sequence/recorder.py` (injected, DI per guardrails).
  Path config `TUSK_ACTION_JOURNAL_PATH`, default `.tusk_runtime/action_journal.jsonl`.

### C2. Surface + docs
- **Change:** tray "open logs" already opens the runtime dir — confirm the journal lands
  there; update `docs/architecture.md` (remove "confirmation out of scope" note, extend
  error table + tool catalog), add `docs/features/approvals.md`.

## Acceptance criteria
- Flagged tool → spoken question → "yes" executes / "no" cancels / silence times out —
  all three verified in the emulated e2e.
- Unflagged flows show zero added LLM calls and no measurable latency change.
- Journal lines appear for both normal and sequence execution paths.

## Out of scope
- Approvals for codex backends (documented limitation; their sandbox is the mitigation).
- GUI approval dialogs — voice/TTS only.
- Flagging shipped gnome tools (revisit when destructive PIM tools arrive).

## Risks
- Yes/no misclassification: keep the approval prompt binary and tiny; unclear → treat as
  decline (safe default).
- The armed slot must never swallow interrupts — `PlaybackGate`/interrupt path stays above
  it in `submit` ordering.
