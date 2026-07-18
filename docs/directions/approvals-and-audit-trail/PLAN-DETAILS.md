# Approvals & Audit Trail — Fine-Grained Execution Plan

Commit-by-commit detail for [PLAN.md](PLAN.md), grounded in the current code
(file:line references against `main` @ `3fb169d`). Where this file and PLAN.md differ,
this file wins — three design points changed once the real code was read (§ Decisions).

Run tests per commit: `docker compose exec tusk pytest tests/kernel/ tests/shells/`.

---

## Decisions (read first)

**D1 — `awaiting_approval` propagates by exception, not by return value.**
The flagged call is hit inside the *executor child* run, but the turn must end for the
*conversation parent* too — otherwise the conversation LLM receives an "awaiting" child
`ToolResult` and improvises. A control-flow exception `ApprovalRequested(pending)` raised
at the dispatch point unwinds `_delegate → parent _step → parent _loop` in one move and is
caught in exactly one place, `AgentOrchestrator.run` (`agent_orchestrator.py:53`), which
converts it to `AgentResult(status="awaiting_approval")`. Mirrors how `InterruptToken`
short-circuits, but synchronous.

**D2 — Resume executes the approved call deterministically, no LLM in the loop.**
After "yes", the pending call runs directly through the dispatcher (registry lookup +
records), *then* a normal executor run wraps up with the result already in session
history. If the user says yes, the action happens — never "the model chose not to".
Bonus: no one-shot `approved_call` token plumbing through `AgentRunRequest.metadata`; the
in-loop gate stays a pure predicate (a flagged call *always* stops the loop — a repeat
attempt in the wrap-up run just asks again, which is correct).

**D3 — The journal is a `Store` decorator, not a new recorder dependency.**
`StepRecorder` and the sequence `Recorder` are constructed internally
(`agent_runtime.py:28`, orchestrator `_init_components`), so injecting a journal there
means threading a parameter through four constructors. Instead `JournalingStore` wraps
`FileStore` (both implement `Store`), watches tool-result and approval events flow through
`append_event`, and emits JSONL. One wiring line in `startup.py`.

---

## Commit 1 — `requires_approval` flag (manifest → registry)

**Tests first** (`tests/kernel/`, mirror existing adapter-manager/registry test modules):
- `test_requires_approval_defaults_false` — a manifest tool without the key.
- `test_requires_approval_parsed_from_manifest` — `tools: {send: {requires_approval: true}}`.
- `test_kernel_tools_default_unflagged` — `start_dictation`/`start_coding`/`switch_model`.

**Changes:**
- `tusk/kernel/tools/registered_tool.py:10` — add `requires_approval: bool = False`
  (file is 19 lines; stays trivially under cap).
- `tusk/kernel/core/adapter_manager.py:98-100` — one line beside the existing flag reads:
  `requires_approval=flags.get("requires_approval", False)`.

## Commit 2 — planner catalog marker + sequence exclusion

**Tests first:**
- `test_catalog_marks_requires_approval` — `AgentToolCatalog.prompt_text()` includes a
  `requires approval` annotation (same style as the `sequence_callable` marker).
- `test_promoter_skips_flagged_tools` — a linear plan containing a flagged tool is *not*
  promoted to sequence mode.
- `test_plan_validator_rejects_flagged_tools` — a handcrafted sequence plan containing a
  flagged tool fails pre-execution validation (defense in depth vs. the promoter).

**Changes:** `tusk/kernel/agent/agent_tool_catalog.py`,
`tusk/kernel/agent/planner/sequence_promoter.py`,
`tusk/kernel/agent/tool_sequence/plan_validator.py` — each needs registry flag access;
promoter/validator signatures to be confirmed at implementation (both already consult
`sequence_callable`, so the flag travels the same path). Planner prompt
(`core/agent_profiles.py`) gains one sentence: flagged tools force `execution_mode=normal`.

## Commit 3 — pending schema + exception + awaiting result

**Tests first:**
- `test_pending_approval_roundtrip` — dataclass ↔ `AgentResult.payload` dict.
- `test_result_factory_awaiting` — `ResultFactory.awaiting()` persists a
  `session_finished` event with status `awaiting_approval` and the question as the
  assistant message (so history/gatekeeper context see it).

**Changes (new files, kernel-internal — no `tusk/shared` schema needed):**
- `tusk/kernel/agent/pending_approval.py` (~25 lines):
  ```python
  @dataclass(frozen=True)
  class PendingApproval:
      call: ToolCall                    # reuses shared schema
      executor_session_id: str
      original_request: AgentRunRequest # for the wrap-up run (session_refs, tool names)
      question: str
      def to_payload(self) -> dict: ...
      @classmethod
      def from_payload(cls, payload: dict) -> "PendingApproval": ...
  ```
- `tusk/kernel/agent/approval_requested.py` (~10 lines): `class ApprovalRequested(Exception)`
  carrying a `PendingApproval`.
- `tusk/kernel/agent/runtime/result_factory.py:24` — add
  `awaiting(session_id, pending) -> AgentResult` beside `cancelled()`; question text is
  built here: `f"This will run {call.tool_name}. {args_summary}. Yes or no?"` (extract
  `_args_summary`, ≤10 lines).

## Commit 4 — the gate in `AgentRuntime`

**Tests first** (scripted LLM + fake executor, pattern of existing runtime tests):
- `test_flagged_call_raises_approval_requested` — loop reaches a flagged tool → raises,
  nothing executed, `approval_requested` event recorded.
- `test_unflagged_call_unaffected` — zero behavior change without the flag.
- `test_orchestrator_converts_to_awaiting_result` — nested conversation→executor run:
  `AgentOrchestrator.run` returns `status="awaiting_approval"`; the *conversation* LLM is
  never called again after the raise (assert call counts on the fake).

**Changes:**
- `tusk/kernel/agent/agent_runtime.py`: constructor gains
  `requires_approval: Callable[[str], bool]` (DI, no registry import — orchestrator
  passes `lambda name: registry.requires_approval(name)`); in `_step` (line 80), before
  `result = executor(tool_call, session_id)`:
  ```python
  if self._requires_approval(tool_call.tool_name):
      raise ApprovalRequested(self._pending(session_id, tool_call))
  ```
  `_pending` records the `approval_requested` event via `StepRecorder` and builds the
  `PendingApproval` (original request reaches `_loop` via one added parameter from
  `run()` — signatures stay under the line rule).
- `tusk/kernel/agent/agent_orchestrator.py:53` — `run()` wraps `self._run(request, ())`
  in `try/except ApprovalRequested` → `self._results_awaiting(exc.pending)` (uses
  `ResultFactory.awaiting`, persisting against the executor session).
- `tusk/kernel/tools/tool_registry.py` — add `requires_approval(name) -> bool` lookup.

## Commit 5 — deterministic resume + decline

**Tests first:**
- `test_resume_executes_pending_call` — `resume_approved(pending)`: dispatcher executes
  exactly the pending call (fake registry records args), `approval_granted` + step events
  land in the executor session, then the wrap-up executor run receives history containing
  the result and its reply is returned.
- `test_resume_flagged_again_asks_again` — wrap-up run trying another flagged call raises
  again (second question), proving no approval token leaks.
- `test_decline_records_and_skips` — `record_declined(pending)`: `approval_declined`
  event, registry never called.

**Changes:**
- `tusk/kernel/agent/agent_orchestrator.py` — two public methods (~10 lines each):
  `resume_approved(pending) -> AgentResult` (dispatch via `self._dispatcher.dispatch`
  with `allowed={call.tool_name}`; append events; then `self._run(replace(
  pending.original_request, instruction=_WRAP_UP, session_id=pending.executor_session_id
  ), ())`) and `record_declined(pending) -> None`.
- Executor system prompt (`core/agent_profiles.py`): one line — "when the last event is an
  approved, already-executed action, summarize and call done; do not repeat it."

## Commit 6 — `ApprovalSlot` in `KernelAPI`

**Tests first** (`tests/kernel/modes/approval/`):
- `test_armed_slot_consumes_yes` → resume callback invoked, reply spoken.
- `test_armed_slot_consumes_no` → decline callback, reply "Cancelled."
- `test_unrelated_command_cancels_then_routes` — verdict `other`: slot disarms, returns
  `None`, `KernelAPI._route` falls through to normal routing *in the same submit*.
- `test_ambient_keeps_pending` — verdict `ignore`: silent `KernelResponse(True, "")`.
- `test_timeout_auto_cancels` — fake timer fires → disarmed, `approval_declined(timeout)`.
- `test_interrupt_style_stop_cancels` — "stop" classifies as decline.

**Changes (new package `tusk/kernel/modes/approval/` — `modes/` is at the 12-file cap):**
- `approval_slot.py` — `ApprovalSlot`: `arm(pending, on_resume, on_decline)`,
  `active`, `process_text(text) -> KernelResponse | None` (None = disarmed, not consumed),
  `threading.Timer` for `TUSK_APPROVAL_TIMEOUT_SECONDS` (default 60, `ConfigFactory`),
  timer cancelled on any resolution. On-start/on-stop callbacks mirroring
  `ModeSlot.set_callbacks` (`mode_slot.py:28`) for the gatekeeper swap.
- `approval_verdict_gate.py` — LLM yes/no/other/ignore classifier on the
  `stop_gate`-with-`gatekeeper`-fallback slot (same acquisition as
  `kernel_api.py:127`); structured-output schema
  `{"verdict": "approve|decline|other|ignore"}`; double LLM failure → `decline` (safe
  default, spoken as cancelled).
- `approval_prompt.py` — the verdict prompt (binary question repeated verbatim, examples
  for "yes do it", "no leave it", "actually open firefox" → other, cough/noise → ignore).
- `kernel_api.py:69` — `_route` starts with:
  ```python
  if self._approval.active:
      consumed = self._approval.process_text(text)
      if consumed is not None:
          return consumed
  ```
  plus `arm_approval(pending)` / `set_approval_callbacks(...)` passthroughs.

## Commit 7 — surfacing from the backend + wiring

**Tests first:**
- `test_main_agent_awaiting_arms_and_speaks_question` — orchestrator returns awaiting →
  `on_awaiting` fired with reconstructed `PendingApproval`, reply text is the question.
- `test_fallback_backend_passes_awaiting_through` — `fallback_agent_backend.py:29` treats
  only `"failed"` specially; regression-pin that awaiting is untouched.
- `test_command_kind_awaiting` — the fast-command path (`main_agent.py:38`) arms too.

**Changes:**
- `tusk/kernel/core/main_agent.py:45` — `_finished` gains an awaiting branch: fire
  injected `on_awaiting(PendingApproval.from_payload(result.payload))`, return
  `result.reply_text()` (the question). Constructor: optional `on_awaiting` callable.
- `tusk/kernel/core/startup.py` — wire `on_awaiting=kernel.arm_approval` (post-construction
  setter, same pattern as `attach_coding_router`); resume/decline callbacks bind to
  `orchestrator.resume_approved` / `record_declined`.

## Commit 8 — voice-shell gatekeeper swap

**Tests first** (`tests/shells/`):
- `test_approval_gatekeeper_forwards_everything` — no LLM call in the shell gatekeeper;
  bare "yes" reaches `kernel.submit` (classification is the kernel slot's job).
- `test_swap_on_arm_and_restore` — arm → slot swapped to `PlaybackGate(ApprovalGatekeeper)`;
  resolve → base restored (assert via `GatekeeperSlot._inner` type).

**Changes:**
- `shells/voice/stages/gate/approval_gatekeeper.py` — forward-all `Gatekeeper` (~20
  lines; `StopGatekeeper` minus stop detection).
- `shell_loader.py:96` — third `_wire_mode`-style call using
  `kernel.set_approval_callbacks`; reuse `_guarded()` so TTS-echo/interrupt behavior
  during the question playback matches modes exactly.

## Commit 9 — action journal

**Tests first:**
- `test_journal_line_per_tool_result` — one JSONL object (ts, session, tool, args
  summary, success, message ≤200 chars) per tool-result event, normal and sequence paths.
- `test_journal_approval_verdicts` — `approval_requested/granted/declined` events emit
  lines with `verdict`.
- `test_journal_write_failure_swallowed` — unwritable path → logged once, never raised.
- `test_non_tool_events_ignored` — message/session events emit nothing.

**Changes:**
- `tusk/kernel/agent/session/journaling_store.py` — `JournalingStore(Store)` decorator:
  delegates everything; `append_event` additionally routes matching event types to
  `ActionJournal` (exact event-name constants confirmed from `StepRecorder`/sequence
  `Recorder` at implementation).
- `tusk/kernel/agent/session/action_journal.py` — append-only JSONL writer,
  `TUSK_ACTION_JOURNAL_PATH` (default `.tusk_runtime/action_journal.jsonl`).
- `startup.py` — `FileStore(...)` → `JournalingStore(FileStore(...), journal)`. One line.

## Commit 10 — e2e + docs

- `demos/approval_demo_adapter/` — fake MCP adapter with a flagged `pretend_send` tool
  (pattern: `demos/editor_emulator/`), plus transcripts: approve / decline / unrelated /
  timeout. Run via `TUSK_SHELLS=emulator` (the emulator bypasses the voice gatekeeper, so
  kernel-side classification is fully exercised without audio).
- Docs: `docs/architecture.md` — drop the "confirmation out of scope" note (§ Notes),
  add the slot to the submit routing description, extend the error table (verdict-gate
  double failure → decline) and env-var tables; new `docs/features/approvals.md`
  (flow, config keys, codex-backend limitation, journal format).

---

## Edge cases (each is a test somewhere above)

| Case | Behavior |
|---|---|
| "yes" while TUSK still speaks the question | `PlaybackGate` path identical to modes; answer after playback is the supported v1 flow |
| Unrelated command while pending | cancel + route the command in the same submit (no lost utterance, no deadlock) |
| Timeout with no reply | silent auto-cancel; journal records `timeout`; next utterance routes normally |
| Second flagged tool in one task | second question — approvals are per-call by design |
| Kernel restart while pending | pending is in-memory only → dropped; nothing was executed, so safe |
| Codex backend turn | never raises `ApprovalRequested` (different pipeline); documented limitation |
| Interrupt token set while pending | idle worker → "stop" is a normal utterance → verdict `decline` |

## Explicitly not building (v1)
Tray/GUI approval UI; `AppMode` enum extension for the tray icon; persistent pending
across restarts; per-tool approval memory ("always allow X"); batch approvals; journal
rotation (`# ponytail:` comment with the ceiling: rotate when a real user's file hurts).

## Open items to confirm during implementation
1. Exact event-name constants in `StepRecorder`/sequence `Recorder` (Commit 9 filter).
2. `SequencePromoter`/`PlanValidator` current signatures for flag access (Commit 2).
3. Whether `GateResult`/emulator paths ever call `submit(kind="command")` while a pending
   approval is armed — the slot intentionally consumes those too; confirm no caller relies
   on bypassing it.
