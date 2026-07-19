# Coding Vertical — Fine-Grained Execution Plan

Commit-by-commit detail for [PLAN.md](PLAN.md), grounded against `main` @ `3fb169d`.
Tests: `docker compose exec tusk pytest tests/adapters/ tests/kernel/`.

## Corrections vs. the assessment (the code moved on)

- **`LineAnchoredEditStrategy` is no longer dormant.** `ToolRuntime._register_coding`
  already wires `VerifiedEditStrategy(LineAnchoredEditStrategy(), FullReplaceEditStrategy())`
  (`tool_runtime.py:29-33`): line-anchored is applied first, the buffer is read back, and
  full-replace repairs drift. PLAN.md step B3's "wire the dormant strategy" is obsolete.
- **The actual gap is upstream:** the coding adapter always emits ONE whole-buffer
  replace op (`adapters/coding/server.py:40, 47-54` — `target_start=1`,
  `target_end=len(old)`, `full_buffer=new`), so line-anchored application degenerates to
  select-all + paste every time. Targeted edits require the *adapter* to emit real
  per-range operations.
- **`EditorDriver` already has navigation** (`goto_line`, `select_range` —
  `interfaces/editor_driver.py:13-16`); "navigation commands" are a planner/adapter
  vocabulary problem, not a driver problem.

## Milestone A — Targeted operations + semantic grounding (adapter-only)

### Commit A1 — diff-based operations
- **Tests** (`tests/adapters/` coding server tests):
  - single-line change in a 30-line buffer → ONE `replace` op spanning just that line,
    `full_buffer` still attached (feeds `VerifiedEditStrategy`'s drift check);
  - pure insertion → `insert` op at the right line; pure deletion → `delete` op;
  - scattered changes → multiple ops **in descending line order** (so earlier
    applications don't shift later targets);
  - unchanged buffer → zero ops, success message "no change".
- **Change:** `adapters/coding/edit_operation_differ.py` — `EditOperationDiffer` over
  `difflib.SequenceMatcher(a=old_lines, b=new_lines).get_opcodes()` mapping
  replace/insert/delete opcodes to the existing op dict shape (`server.py:47-54`
  retires); `server.py:_tool_process_intent` (`server.py:33-41`) calls it. Planner and
  prompt untouched — the LLM still returns the whole buffer; the differ extracts the
  minimal ops. This makes today's gedit path stop rewriting whole files per edit.
- **Latency note:** difflib on ≤2k-line buffers is sub-millisecond; the win is removing
  the full-buffer paste (~0.4 s clipboard round-trip) for small edits.

### Commit A2 — tree-sitter symbol map
- **Tests:**
  - Python and JS/TS fixture buffers → `[{name, kind, start_line, end_line}]` for
    functions/classes/methods;
  - unparseable buffer → empty map, no exception;
  - prompt block rendering is compact (one line per symbol, capped at 40 symbols).
- **Change:** `adapters/coding/symbol_map_builder.py`; `tree_sitter` +
  `tree-sitter-python`, `tree-sitter-javascript` in `adapters/coding/requirements.txt`
  (venv-isolated per `adapter_env_builder`). Language pick: `CODING_LANGUAGE` env default
  `python`, overridable per session later (open item 2).

### Commit A3 — grounded planner prompt
- **Tests:** with a non-empty symbol map, the planner message contains a `<symbols>`
  block between buffer and instruction; with fixture LLM responses, "delete the function
  called parse_header" produces a buffer without it (parse of the fixture, not live LLM).
- **Change:** `CODING_PLANNER_PROMPT` + message assembly in
  `adapters/coding/coding_edit_planner.py:32-35` (one added prompt line: symbols are
  hints for locating code, not content to reproduce).
- **Verify (e2e):** extend the `demos/` coding transcript: seed 30-line buffer, "delete
  the function called X", "add a docstring to class Y" — assert final buffer snapshot
  (`.tusk_runtime/editor_emulator_buffer.txt` pattern).

## Milestone B — VS Code bridge

### Commit B1 — protocol + extension
- **Change:** new top-level `editor-bridges/vscode/` (TypeScript, own `package.json`, no
  deps beyond `@types/vscode`): listens on `.tusk_runtime/vscode-bridge.sock` (Unix
  socket), line-delimited JSON:
  `{"op":"ping"}` → `{"ok":true}`;
  `{"op":"read_buffer"}` → `{"buffer":"...","version":N}`;
  `{"op":"apply_edit","start_line":A,"end_line":B,"text":"..."}` →
  `{"ok":true,"version":N+1}` (1-based inclusive lines, `end_line=start_line-1` encodes
  pure insert — matches `EditOperation` semantics);
  `{"op":"goto_line","line":N}`, `{"op":"press_keys"...}` unsupported → `{"ok":false}`.
  Targets the *active editor*; refuses when none.
- **Tests:** Python-side contract tests against a scripted fake socket server (B2); the
  TS extension stays under ~120 lines, reviewed by hand; marketplace packaging deferred
  (sideload via `code --install-extension` of a local `.vsix`).

### Commit B2 — `VsCodeEditorDriver`
- **Tests** (`tests/kernel/modes/`): implements every `EditorDriver` method
  (`interfaces/editor_driver.py:8-28`):
  `read_buffer` → bridge; `replace_buffer` → whole-range `apply_edit`;
  `select_range`+`paste` collapse to one ranged `apply_edit` (driver records the last
  selection, `paste` consumes it — same trick the strategies rely on);
  `goto_line` → bridge; `type_text` → insert at cursor; `press_keys` → unsupported
  `RuntimeError` (nothing in the coding path calls it on this driver — the strategies use
  select/paste/delete via `select_range` + `press_keys("Delete")`… so map
  `press_keys("Delete")` on an active selection to a ranged empty-text `apply_edit`;
  anything else raises). Socket absent → constructor probe fails cleanly.
- **Change:** package move per the directory rule: `tusk/kernel/modes/` is at the
  12-file cap → new `tusk/kernel/modes/editor_drivers/` holding
  `input_automation_editor_driver.py` (moved verbatim) + `vscode_editor_driver.py` +
  `driver_selector.py` (B3). Naming decision: keep the full class names
  (`InputAutomationEditorDriver`) — dropping the group suffix would leave
  `InputAutomation`/`Vscode`, which lose the "editor driver" meaning (sanctioned
  exception in the directory rule). Pure move + import updates in its own commit half.

### Commit B3 — driver selection at session start
- **Tests:**
  - focused window `wm_class` contains `Code` *and* socket ping succeeds → bridge driver;
  - otherwise input-automation;
  - `TUSK_CODING_DRIVER=input_automation|vscode` overrides (config key);
  - the *router* uses the driver chosen at start (selector holds the active driver).
- **Change:** `editor_drivers/driver_selector.py` — `DriverSelector` constructed in
  `ToolRuntime._register_coding` (`tool_runtime.py:29-33`) with both drivers; injected
  into `StartCodingTool` (replacing the single `driver` param,
  `start_coding_tool.py:16-20` — `read_buffer` goes through `selector.choose()` which
  pins `selector.active` for the session) and into `CodingRouter` (which currently holds
  one driver, `coding_router.py:12-17` — it reads `selector.active` instead). Focused
  window comes from the existing `gnome.get_active_window` tool through the registry.
- **Verify live:** gedit session → input automation (unchanged); VS Code session with
  extension → bridge (watch the log tag).

### Commit B4 — cheap read-back + resync
- **Tests:**
  - with the bridge driver, `VerifiedEditStrategy`'s read-back costs one socket call (no
    clipboard, no `ClipboardGuard`) — behavioral: clipboard tools never invoked;
  - buffer `version` mismatch before `process_intent` → `coding.resync_session` called
    with the fresh buffer, then the intent proceeds against it;
  - manual VS Code edits between intents → next intent plans against the edited buffer
    (fixture flow).
- **Change:** adapter tool `resync_session(session_id, buffer)` in
  `adapters/coding/server.py` (+ schema catalog entry, `planner_visible=false`);
  `CodingRouter._ensure_synced(state)` pre-check (extracted, ≤10 lines) using
  `driver.read_buffer` when the active driver is the bridge (cheap); for input-automation
  the check is skipped (cost) and the spoken intent "sync with my edits" triggers it
  explicitly (gate prompt vocabulary already forwards everything — the *adapter planner*
  can't do it, so route: `CodingRouter.process` recognizes the resync result shape from
  a tiny `should_resync` classifier? — **no**: keep v1 dumb, a literal utterance check is
  a hard-coded phrase, which the guardrails forbid for stop-detection but this is a
  command, not a gate… simplest honest v1: resync automatically for bridge, manual resync
  ships only with the bridge; input-automation keeps today's semantics). Record this
  scope cut in the feature doc.
- **Verify live:** VS Code: spoken edits interleaved with manual typing — no drift, no
  clobber; note latency vs. gedit path in the PR description (expect bridge to win).

## Milestone C — Navigation vocabulary

### Commit C1 — "go to X" intents
- **Tests:** adapter: intent "go to the function parse_header" with a symbol map →
  response `{"navigate_to_line": N}` (new optional field beside `operations`); router:
  navigation response → `driver.goto_line(N)`, spoken reply "" (silent success);
  unknown symbol → failure message "I can't find parse_header."
- **Change:** planner prompt + schema gain the optional field
  (`coding_edit_planner.py:17-22` `_SCHEMA`); `CodingRouter._apply` handles it before
  operations. **No `EditOperation` schema change** — navigation stays out of the edit
  path entirely (corrects PLAN.md C1, which anticipated a schema extension).

### Commit C2 — docs
- **Change:** refresh `docs/features/pair-coding-mode.md` (it still says line-anchored is
  unwired — stale even against `main`) and `docs/architecture.md` coding sections
  (driver package, selector, bridge, targeted ops).

## Edge cases

| Case | Behavior |
|---|---|
| VS Code closes mid-session | bridge socket errors → router failure reply "I couldn't apply that edit."; stop still works (adapter-side session) |
| Two VS Code windows | bridge targets the active editor; driver selection pinned at session start |
| Symbol name spoken fuzzily ("parse header" vs `parse_header`) | planner prompt instructs normalization (spaces→underscores, case-insensitive); C1 test covers |
| Huge buffer (>2k lines) | symbol map capped at 40 entries; differ is O(n); full_buffer payloads already flow today |
| Mixed language file (JS in HTML) | v1 parses by configured language only; degrade = empty map (today's behavior) |

## Explicitly not building (v1)
vim/JetBrains bridges; LSP integration; multi-file awareness; marketplace publication;
dictation-inside-coding hybrid; undo grouping (VS Code's native undo applies per
`apply_edit`).

## Open items to confirm during implementation
1. `workspace.applyEdit` vs `TextEditor.edit` in the extension (atomicity + undo
   behavior) — spike in B1.
2. Per-session language detection (active window title extension vs. `CODING_LANGUAGE`) —
   decide in A2 with a test either way.
3. Whether `VerifiedEditStrategy`'s read-back-per-op should batch for multi-op intents
   (A1 makes multi-op common; one read-back after the *batch* may suffice — measure).
