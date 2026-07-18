# Plan: Deepen the Coding Vertical

**Branch:** `feature/coding-symbols`, then `feature/vscode-bridge` · **Depends on:**
nothing (Milestone A); B benefits from
[reliability](../reliability-and-wayland/README.md) landing first but doesn't require it ·
**Unblocks:** the "hands-free coding" preset in
[vertical-packaging](../vertical-packaging/README.md).

Milestone A is adapter-only and improves *today's* experience with the existing
input-automation driver. B is the editor-native bridge — the strategic piece. C grows the
command language on top of both. Ship A before B: it derisks the planner prompt work and
delivers user-visible value in days, not weeks.

## Milestone A — Semantic grounding (adapter-only)

### A1. Symbol map from tree-sitter
- **Tests:** `tests/adapters/` — `SymbolMapBuilder` over sample Python/JS buffers returns
  functions/classes/methods with 1-based line ranges; unparseable buffer → empty map
  (never an exception); map renders to a compact prompt block (name · kind · lines).
- **Change:** `adapters/coding/symbol_map_builder.py` (one class);
  `tree_sitter` + language packs in the coding adapter's `requirements.txt`
  (venv-isolated — the kernel image doesn't grow).

### A2. Grounded planner prompt
- **Tests:** `CodingEditPlanner` prompt includes the symbol map when non-empty; planner
  output for "delete the function called parse_header" targets the mapped range (fixture
  LLM responses — no live LLM in unit tests).
- **Change:** prompt assembly in `coding_edit_planner.py`; language detection from the
  focused window title / stated language, defaulting to Python.

### A3. E2E on the emulated editor
- **Verify:** extend `demos/` transcript: seed a 30-line buffer, "delete the function
  called X", "add a docstring to class Y" — full-replace strategy applies; compare
  scenario-for-scenario against the e2e baseline (known harness flakiness).

## Milestone B — VS Code bridge

### B1. Protocol + extension skeleton
- **Change:** new top-level `editor-bridges/vscode/` (TypeScript extension, its own
  build): line-delimited JSON over a local Unix socket
  (`.tusk_runtime/vscode-bridge.sock`) — `read_buffer`, `apply_edits` (via
  `workspace.applyEdit`), `get_cursor`, `buffer_version`. Mirror the MCP framing style;
  no npm deps beyond VS Code API.
- **Tests:** protocol contract tested from Python against a scripted fake socket server
  (the TS side stays thin enough to review by hand; extension CI is out of scope v1).

### B2. `VsCodeEditorDriver` + driver package
- **Tests:** `tests/kernel/modes/` — driver implements `EditorDriver`; `read_buffer`
  returns bridge content; `apply_edits` maps `EditOperation` line ranges to bridge edits;
  socket absent → driver reports unavailable (selection falls back).
- **Change:** `tusk/kernel/modes/` is at the 12-file cap → new package
  `tusk/kernel/modes/editor_drivers/` holding the new driver + the moved
  `InputAutomationEditorDriver` (file/class naming per the directory-organization rule —
  drop the group suffix on move unless the shortened name goes generic). Pure move for the
  existing driver: no logic changes in the same PR.

### B3. Capability-driven strategy selection
- **Tests:** `EditorDriver.supports_readback` — `False` for input automation, `True` for
  the bridge; `ToolRuntime` wiring picks `LineAnchoredEditStrategy` for readback-capable
  drivers and keeps `FullReplaceEditStrategy` otherwise; line-anchored application via the
  bridge touches only the targeted lines (no select-all, no clipboard, no
  `ClipboardGuard`).
- **Change:** property on the `EditorDriver` ABC (`tusk/kernel/interfaces/editor_driver.py`),
  strategy choice in `ToolRuntime` wiring, un-dormant
  `modes/edit_strategies/line_anchored_edit_strategy.py` (wire + fix what its first real
  use reveals — it has never run in anger).

### B4. Driver selection at session start
- **Tests:** `StartCodingTool` picks the bridge driver when the focused window class
  matches VS Code *and* the socket answers a ping; otherwise input automation. Explicit
  override `TUSK_CODING_DRIVER=input_automation|vscode` for debugging.
- **Change:** selection helper in the coding start path; config key.

### B5. Drift resync
- **Tests:** when `supports_readback`, each `process_intent` is preceded by a cheap
  buffer-version check; on mismatch the session buffer is refreshed via a new
  `coding.resync_session(session_id, buffer)` adapter tool before planning; also exposed
  as a spoken intent ("sync with my edits") for the non-readback driver.
- **Change:** adapter tool in `adapters/coding/server.py` + session store; router
  pre-check in `CodingRouter` (guard the ≤10-line rule — extract `_ensure_synced`).

### B6. Live verification
- **Verify:** real VS Code session: seed buffer, mixed spoken edits and *manual* edits
  interleaved — no drift, targeted edits don't clobber manual ones. Record the
  gedit-vs-VS Code latency numbers (expect the bridge to win — no paste round-trip).

## Milestone C — Richer command language

### C1. Navigation operations
- **Tests:** schema round-trip for a navigation op ("go to function X" → symbol map lookup
  → target line); bridge driver reveals the range; input-automation driver falls back to a
  goto-line keystroke sequence where the editor supports it, else speaks "can't navigate
  here".
- **Change:** extend `tusk/shared/schemas/edit_operation.py` (or a sibling
  `NavigationOperation` — decide at implementation; one schema PR either way), planner
  prompt vocabulary, both strategies.

### C2. Docs
- **Change:** refresh `docs/features/pair-coding-mode.md` and the architecture doc's
  coding sections (driver package move, strategy selection, bridge).

## Acceptance criteria
- "Delete the function called X" works on today's gedit path (A) and via VS Code with
  line-anchored edits (B), verified in e2e + live.
- Manual edits during a VS Code session never cause drift (B5/B6).
- No kernel file over 100 lines; `modes/` back under the directory cap after the package
  move.

## Out of scope
- Editors beyond VS Code (the driver package is the seam; vim/JetBrains are future
  bridges); LSP integration (tree-sitter is enough for v1 grounding); multi-file
  awareness; dictation-within-coding hybrid.

## Risks
- `LineAnchoredEditStrategy` is unexercised code — treat B3 as its real shakedown; keep
  full-replace one config flip away.
- Tree-sitter grammars per language: start with Python + JS/TS, listed explicitly; other
  languages degrade to ungrounded prompts (today's behavior, not a regression).
- VS Code extension review/packaging (marketplace) deferred — sideload for now.
