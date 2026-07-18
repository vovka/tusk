# Direction: Approvals & Action Audit Trail

**Research basis:** the "chatbot vs. assistant that actually does things" trust gap; the
predicted category winner ships "better approvals/safety UX"
([market research](../../market-research-reddit-2026-07.md)).
**Verdict:** fits the current architecture well. All tool execution already flows through
two choke points; the mode machinery already solves "route the next utterance to a pending
consumer". No layer boundaries move. `docs/architecture.md` § Notes currently declares
dangerous-action confirmation out of scope — this direction reverses that.

**Diagram:** [approval flow](approval-flow.md)

## What the architecture already provides

- **Single dispatch choke points.** Every action goes through `ToolRegistry.get(name).execute(args)`,
  called from exactly two places: the `AgentRuntime` executor loop and `tool_sequence/executor.py`.
  An approval check wraps both without touching adapters or shells.
- **Per-tool manifest flags precedent.** `adapter.json` already carries `planner_visible`,
  `sequence_callable`, `settle_ms` per tool; a `requires_approval` flag follows the same path
  (manifest → `RegisteredTool` field → registry filtered views).
- **Audit trail is ~80% built.** The session `FileStore` already logs every
  `step_requested`/`step_result` event per run (`tusk/kernel/agent/session/`,
  `runtime/step_recorder.py`, `tool_sequence/recorder.py`). An audit trail is a readable
  projection of these events, not new instrumentation.
- **Pending-consumer pattern exists.** `ModeSlot` + gatekeeper swap (dictation/coding) shows
  how `KernelAPI.submit` routes the *next* utterance to a waiting component; `SpeechStopGate`
  shows a cheap yes/no LLM classifier. An "awaiting approval" state reuses both patterns.
- **Spoken prompt path exists.** The TTS/ack path (`CommandWorker` → `SpeechPlayback`) can ask
  "Send this email to X — yes or no?" with no new plumbing.

## Gaps

- No approval gate anywhere; the executor fires tools immediately.
- `AgentRuntime` runs a turn to completion — there is no pause/resume of an in-flight run.
  Blocking mid-run is not an option: the confirmation utterance arrives through the same
  serialized `KernelAPI.submit` lock the run holds.
- Codex backends run with `approval-policy: "never"` and their own adapter instances —
  tusk-side approval gating cannot intercept them.
- No user-facing view of what was done (session logs are debug artifacts).

## Required changes

1. **[shared/adapters]** `requires_approval: true` per-tool manifest flag → `RegisteredTool`
   field. Flag the genuinely destructive tools only (send/delete/close-unsaved), not everything.
2. **[kernel]** Approval as a *turn boundary*, not a blocking wait: when the executor reaches a
   flagged tool, the run persists its state and returns
   `AgentResult(status="awaiting_approval", pending_call)`. Resume = re-enter the executor
   profile against the persisted session (the `Store` already holds full message history);
   needs a resume entry point in `AgentOrchestrator`.
3. **[kernel]** A `PendingApprovalSlot` on `KernelAPI` (sibling of the dictation/coding
   `ModeSlot`s, checked first in `submit`): consumes the next utterance, classifies yes/no via
   the gatekeeper LLM slot (`SpeechStopGate`-style prompt), then resumes or cancels.
4. **[kernel]** Sequence mode: `PlanValidator` forbids `requires_approval` tools in compiled
   sequences (one rule) — such plans stay in normal executor mode where the gate lives.
5. **[kernel]** `ActionJournal`: append-only JSONL projection of session events (tool, args
   summary, outcome, approval verdict), surfaced via the existing tray "open logs" action.
6. **[docs]** Codex backends documented as outside the approval boundary; mitigation is their
   sandbox mode, not the tusk gate.

## Risks & notes

- Latency: one extra voice round-trip per flagged action — acceptable precisely because the
  flag list is short.
- False sense of safety if adapters add destructive tools without the flag — manifest review
  becomes a required habit (guardrail check could enforce flag presence for known-risky verbs).
- The approval question must survive the gatekeeper: while a `PendingApprovalSlot` is active
  the voice shell should treat "yes"/"no" as directed speech (same swap trick modes use).
