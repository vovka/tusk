# Direction: Deepen the Coding Vertical

**Research basis:** semantic edit commands for IDEs are the loudest underserved niche —
voice-coding after stroke (123 upvotes, r/csharp), Hands-Free Coding (608 points, HN),
"brak VS Code/IDE-підтримки" as a recurring pain
([market research](../../market-research-reddit-2026-07.md)). This is TUSK's most
differentiated asset: LLM-semantic edits where Talon offers command grammars.
**Verdict:** the mode/driver/strategy seams were designed for exactly this growth; the
architecture doc itself names "a future VS Code extension implementing `EditorDriver`" as
the drift fix. Work concentrates in one new editor bridge and the coding adapter — no
shared-schema change turned out to be needed (navigation rides a response field, not a
new op; see PLAN-DETAILS). The bridge itself (local socket + VS Code extension) is
inherently cross-OS: it carries unchanged to Windows/macOS once desktop adapters for
those platforms exist.

**Diagram:** [editor driver seam](editor-driver-seam.md) · **Plan:** [PLAN.md](PLAN.md)

## What the architecture already provides

- **The whole mode stack.** `ModeSlot`/`AdapterMode`/`CodingRouter`/`ModeGate` solve
  utterance routing, stop detection, and TTS suppression — none of it changes.
- **The two seams that matter.** `EditorDriver` ABC (how edits reach an editor) and
  `EditApplicationStrategy` ABC (how operations are applied). Better implementations slot
  in without kernel changes.
- **A self-repairing strategy chain, already wired.** `ToolRuntime` composes
  `VerifiedEditStrategy(LineAnchoredEditStrategy, FullReplaceEditStrategy)`: line-anchored
  application, buffer read-back, full-replace repair on drift (~0.4 s clipboard
  round-trip per edit on the input-automation driver).
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
- **Every edit is a whole-buffer op.** The coding adapter always emits one replace op
  spanning the entire buffer, so the wired line-anchored strategy degenerates to
  select-all + paste — targeted edits need the adapter to emit real per-range operations
  (a diff step; see PLAN-DETAILS).

## Required changes

1. **[new: editor bridge]** A minimal VS Code extension exposing `read_buffer` /
   `apply_edit` / cursor info over a local socket, plus a kernel-side `VsCodeEditorDriver`
   implementing `EditorDriver`. Read-back closes the drift loop and makes edits atomic
   (no clipboard, no `ClipboardGuard` needed on this path).
2. **[kernel/modes]** Driver selection at session start — focused window class + bridge
   ping (gedit → input automation, VS Code → bridge), `TUSK_CODING_DRIVER` override. The
   wired strategy chain stays; the bridge makes its per-edit read-back cheap (one socket
   call instead of a clipboard round-trip).
3. **[adapters/coding]** Ground the planner: tree-sitter parse of the buffer → symbol map in
   the planner prompt (adapter-internal; no kernel change). This is what turns "delete this
   function" from a guess into a lookup.
4. **[adapters/coding]** Resync operation: driver `read_buffer` → `BufferModel` refresh,
   exposed as an explicit "sync with my edits" intent and run automatically on drift signals
   from a feedback-capable driver.
5. **[adapters/coding]** Navigation intents ("go to function X") via an optional
   `navigate_to_line` response field beside `operations` — no `EditOperation` schema
   change needed (corrected from the first draft of this assessment; see PLAN-DETAILS).

## Risks & notes

- Editor-native bridges multiply per editor (VS Code, vim, JetBrains). The `EditorDriver`
  ABC contains the blast radius, but each bridge is its own small product — start with
  VS Code only, keep input automation as the universal fallback.
- Tree-sitter adds a dependency to the coding adapter; adapters have isolated venvs
  (`requirements.txt` → managed venv), so the cost stays out of the kernel image.
- Latency budget: bridge edits remove the paste round-trip, likely *improving* the
  hot-path feel — measure per the latency rule anyway.
