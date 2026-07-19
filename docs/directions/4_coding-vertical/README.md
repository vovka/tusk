# Direction: Deepen the Coding Vertical

**Research basis:** semantic edit commands for IDEs are the loudest underserved niche —
voice-coding after stroke (123 upvotes, r/csharp), Hands-Free Coding (608 points, HN),
"brak VS Code/IDE-підтримки" as a recurring pain
([market research](../../market-research-reddit-2026-07.md)). This is TUSK's most
differentiated asset: LLM-semantic edits where Talon offers command grammars.
**Verdict:** the mode/driver/strategy seams were designed for exactly this growth; the
architecture doc itself names "a future VS Code extension implementing `EditorDriver`" as
the drift fix. Work concentrates in one new editor bridge and the coding adapter; the only
shared-schema touch is extending `EditOperation`.

**Diagram:** [editor driver seam](editor-driver-seam.md) · **Plan:** [PLAN.md](PLAN.md)

## What the architecture already provides

- **The whole mode stack.** `ModeSlot`/`AdapterMode`/`CodingRouter`/`ModeGate` solve
  utterance routing, stop detection, and TTS suppression — none of it changes.
- **The two seams that matter.** `EditorDriver` ABC (how edits reach an editor) and
  `EditApplicationStrategy` ABC (how operations are applied). Today's implementations —
  `InputAutomationEditorDriver` + `FullReplaceEditStrategy` — are the lowest common
  denominator; better ones slot in without kernel changes.
- **A dormant finer-grained strategy.** `line_anchored_edit_strategy.py` exists but is not
  wired in `ToolRuntime`.
- **Adapter-side intelligence.** `CodingEditPlanner` (own LLM slot) + authoritative
  `BufferModel`; `EditOperation` schema with `full_buffer` resync semantics.

## Gaps

- **Fire-and-forget GUI automation.** The input-automation driver cannot read back editor
  state: manual edits drift the model undetected (documented), clipboard juggling is slow on
  large buffers, and full-buffer re-paste is the only resync.
- **No editor-native integration.** The concrete market ask is VS Code; nothing speaks to any
  editor's real API.
- **Plain-text buffer.** No syntax/symbol grounding — "delete this function" rides entirely on
  the LLM reading numbered lines; no tree-sitter/LSP assist, no navigation commands
  ("go to function X").
- **Strategy selection is static.** `FullReplaceEditStrategy` is hardwired; a feedback-capable
  driver should get line-anchored edits instead.

## Required changes

1. **[new: editor bridge]** A minimal VS Code extension exposing `read_buffer` /
   `apply_edit` / cursor info over a local socket, plus a kernel-side `VsCodeEditorDriver`
   implementing `EditorDriver`. Read-back closes the drift loop and makes edits atomic
   (no clipboard, no `ClipboardGuard` needed on this path).
2. **[kernel/modes]** Driver capability flag (`supports_readback`) drives strategy choice in
   `ToolRuntime` wiring: feedback-capable driver → wire the existing
   `LineAnchoredEditStrategy`; GUI-automation driver → keep full-replace. Driver selection by
   focused window class (gedit → input automation, VS Code → bridge).
3. **[adapters/coding]** Ground the planner: tree-sitter parse of the buffer → symbol map in
   the planner prompt (adapter-internal; no kernel change). This is what turns "delete this
   function" from a guess into a lookup.
4. **[adapters/coding]** Resync operation: driver `read_buffer` → `BufferModel` refresh,
   exposed as an explicit "sync with my edits" intent and run automatically on drift signals
   from a feedback-capable driver.
5. **[shared/schemas]** Extend `EditOperation` (or add a sibling op) for navigation/selection
   intents — the one cross-layer schema change in this direction.

## Risks & notes

- Editor-native bridges multiply per editor (VS Code, vim, JetBrains). The `EditorDriver`
  ABC contains the blast radius, but each bridge is its own small product — start with
  VS Code only, keep input automation as the universal fallback.
- Tree-sitter adds a dependency to the coding adapter; adapters have isolated venvs
  (`requirements.txt` → managed venv), so the cost stays out of the kernel image.
- Latency budget: bridge edits remove the paste round-trip, likely *improving* the
  hot-path feel — measure per the latency rule anyway.
