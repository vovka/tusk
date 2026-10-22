# Pair-Coding Mode

## Overview
Voice-driven code editing: each spoken edit intent is sent with the current buffer to an
LLM planner, which returns the complete rewritten buffer; the kernel pastes it into the
focused editor via select-all + clipboard automation.

## Key Files & Structure
- `tusk/kernel/tools/start_coding_tool.py` — agent-visible `start_coding` tool; reads the editor buffer, opens an adapter session. Idempotent: no-ops (`ToolResult(True, "Already in pair-coding mode.")`) if `ModeSlot.active` is already true, so executor retries can't orphan adapter sessions.
- `tusk/kernel/modes/coding_mode.py` — `CodingMode`. While the coding `ModeSlot` is active, `KernelAPI.submit` routes every utterance here. Successful edits reply with an empty string (silent — logged, not spoken); only failures ("I couldn't apply that edit.") are spoken.
- `tusk/kernel/modes/editor/editor_driver.py` — drives the editor via `<desktop>.press_keys` / clipboard tools (`ClipboardGuard` saves/restores clipboard)
- `tusk/kernel/modes/editor/edit_applier.py` — `EditApplier`: applies the line-anchored edit, reads the buffer back, and re-pastes `full_buffer` (select-all + paste) on mismatch
- `adapters/coding/` — stdio MCP adapter: `CodingEditPlanner` (LLM, `CODING_AGENT_MODEL`, default `llama-3.3-70b-versatile` on Groq) plans a full-buffer rewrite per intent; `server.py` holds the session buffer as plain text (`dict[str, str]`), no separate buffer-model class
- `shells/voice/gate/stop_gatekeeper.py` (`StopGatekeeper`) + `tusk/kernel/modes/mode_gate.py` (`ModeGate`, prompts in `mode_gate_prompts.py`) — voice-shell-only stop detection ("stop coding"); bypassed by other shells

## How It Works
1. "Start pair-coding mode" (or "let's start pair coding") → conversation agent → planner → executor calls `start_coding`.
2. `start_coding` reads the focused editor buffer (ctrl+A/C via primary desktop source) and calls `coding.start_coding_session`.
3. Each subsequent utterance → `coding.process_intent`: the planner receives the buffer with **numbered lines** (`1| code`, for the LLM's own reference only) plus the instruction, and returns `{"buffer": "<complete new buffer>"}`. The server wraps this as a single `replace` operation spanning the whole old buffer (`target_start=1`, `target_end=<old line count>`) and updates the session.
4. `CodingMode` applies that one op through `EditApplier` (line-anchored edit, then re-paste `full_buffer` on drift).
5. If the instruction names a line number beyond the buffer's end (e.g. "go to line seven" on a 3-line buffer), the planner is instructed to place the change structurally instead of padding with blank lines — verified working in e2e.

## E2E Test Harness (no X11 needed)
- `shells/emulator_shell.py` — replays a transcript as utterances (`TUSK_SHELLS=emulator`, `TUSK_TRANSCRIPT`, `TUSK_UTTERANCE_PAUSE`)
- `demos/editor_emulator/` — mock desktop adapter (in-memory editor with select-all/copy/paste semantics, `provides_context: true`); bind-mount into `adapters/` so it claims the desktop-source slot ahead of gnome (sorted order); snapshots buffer to `.tusk_runtime/editor_emulator_buffer.txt`
- Run commands: see headers of `demos/coding_session_emulated.txt` (original bug-reproduction transcript) and `demos/coding_session_target_flow.txt` (the user's exact desired flow, used to verify the rewrite)
- Standalone adapter replay (no kernel, no conversation/planner LLM overhead): see the JSON-RPC loop pattern in that harness — `initialize` / `tools/call` line-delimited JSON on stdio; useful for isolating adapter-level behavior per step
- **Precede the first coding utterance with "Open gedit."** even against the mock adapter — without a prior window-open/focus action, the conversation agent sometimes asks "which window would you like me to focus?" instead of calling `start_coding` directly. This is a pre-existing conversational-routing quirk, unrelated to the coding adapter itself.

## Fixed (2026-07-03)
1. **Hallucinated line numbers corrupting the buffer** (the original bug). The planner
   used to return `{operations: [{kind, target_start, target_end, new_text}]}` against an
   *unnumbered* buffer and a bounds-unchecked `BufferModel.with_edit` — the LLM
   guessed line numbers, producing negative splices and out-of-range appends that
   diverged the session buffer irrecoverably. Fixed by switching the planner's contract
   to a full-buffer rewrite (`{"buffer": "..."}`); `BufferModel` is deleted.
2. **Line-number prefixes leaking into the output buffer.** After numbering the buffer
   for the planner's *input*, the LLM sometimes echoed the `N| ` prefixes back in its
   *output*. Fixed with an explicit prompt instruction plus a defensive regex strip
   (`_unnumbered()` in `coding_edit_planner.py`) as a backstop.
3. **`openai/gpt-oss-120b` 400s on the coding schema.** That model is in Groq's
   `_STRICT_SCHEMA_MODELS` (`tusk/providers/llm/groq_llm.py`), which requires
   `additionalProperties: false` on every schema object; the planner's schema lacked it
   (latent while the default model used loose `json_object` mode). Fixed by adding the
   key, matching the existing convention in `tusk/kernel/modes/mode_gate.py`.
4. **Orphaned adapter sessions from executor retries.** Fixed via `ModeSlot.active`
   + an idempotent `StartCodingTool`.
5. **TTS chatter on every edit.** Fixed — successful edits are now silent.

## Fixed (2026-10-03)
- **Crossed replies on the shared MCP stdio pipe.** The stop path runs on the voice thread while the worker thread can still
  be inside `coding.process_intent`; `MCPClient` had no lock and `MCPStdioTransport.write_line` discards unread output, so
  one call could get the other's reply or time out after 30 s (a "hung" stop or a lost edit). `MCPClient._request` is now
  serialised (`tests/shared/mcp/test_mcp_client_concurrency.py`). A stop spoken mid-edit waits for that edit to finish.
- **STT variants of the stop phrase** ("pair-coding", "paired/pear coding", "pair programming", "okay ... please/now") no
  longer fall through to the LLM stop gate (`shells/voice/gate/stop_gatekeeper.py`).

## Known Limitation (not a bug — LLM judgment, verified in e2e)
When a later instruction plausibly overlaps a prior edit (e.g. "log this argument" after
an earlier "insert a console.log('test')" in the same function), the planner may
*replace* the earlier log call rather than add a second one alongside it. The prompt says
to preserve lines the instruction "does not concern," but overlap is genuinely ambiguous
— this is inherent to LLM-driven whole-buffer rewriting, not a structural defect like
(1) above. Each instruction's own stated outcome is still satisfied correctly.

## Known Issues (still open, out of scope for the 2026-07-03 fix)
- **Non-voice shells cannot stop coding mode** — stop detection lives in the voice
  shell's `StopGatekeeper`; via emulator/CLI, "stop coding" is treated as an edit intent.

---
**Last updated**: 2026-07-03 · **Updated by**: Claude · **Exploration depth**: Deep
