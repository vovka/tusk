# Plan: Reliability & Wayland-Native Input

**Branch:** one worktree per phase (`feature/adapter-supervision`, `feature/audio-recovery`,
`feature/wayland-input`, `feature/wayland-windows`) · **Depends on:** nothing ·
**Unblocks:** credible accessibility vertical; Wayland-era survival.

Four phases, independently shippable, ordered by value/effort. A and B are pure
reliability (no new host components) and can land immediately. C and D introduce the
Wayland bridge. Keyboard/typing comes before mouse — dictation and coding are the
verticals that need Wayland first, and they don't need pointer control.

## Phase A — Adapter supervision

### A1. Liveness primitive
- **Tests:** `tests/shared/` — `MCPClient.is_alive` reflects child process state.
- **Change:** expose `poll()` through `MCPStdioTransport` → `MCPClient.is_alive` (2 lines each).

### A2. Registry deregistration
- **Tests:** removing an adapter's tools by prefix; re-registering replaces cleanly.
- **Change:** add/confirm `ToolRegistry.remove_adapter_tools(name)` (the hot-plug watcher
  path may already have a variant — reuse, don't duplicate).

### A3. `AdapterSupervisor`
- **Tests:** with a fake dead client — restart with backoff (1s → 2s → … cap 30s, forever),
  re-handshake + `tools/list`, registry entries swapped; while down, proxy calls return
  `ToolResult(False, "adapter <name> unavailable")` instead of hanging; status surfaced.
- **Change:** new `tusk/kernel/core/adapter_supervisor.py` (daemon thread, DI:
  adapter manager + registry + reporter + log). Down-state check is one guard in
  `MCPToolProxy.execute`. Boundary: supervisor owns process death; the watcher owns
  manifest add/remove — restart logic lives only in the supervisor.
- **Verify:** `kill -9` a running adapter's process in a live session → tools degrade
  politely, adapter returns within backoff, no kernel restart.

## Phase B — Audio & STT resilience

### B1. Mic recovery
- **Tests:** fake `sounddevice` raising `PortAudioError` mid-stream — capture reopens with
  backoff, pipeline continues, `StatusSnapshot.mic` shows error-then-ok; permanent failure
  keeps the process alive with mic status = error (today it crashes the process).
- **Change:** recovery loop in `shells/voice/stages/audio_capture.py` (keep functions ≤10
  lines — extract `_reopen_with_backoff`).

### B2. STT fallback engine
- **Tests:** primary engine raising → fallback transcribes; N consecutive successes probe
  back to primary; no fallback configured → current behavior.
- **Change:** `tusk/providers/stt/fallback_stt.py` (`FallbackSTT` wrapping two engines,
  implements `STTEngine`); `STTEngineFactory` builds it when `STT_ENGINE_FALLBACK` is set;
  config key. Default recommendation: `groq` primary + `whisper` fallback.
- **Verify:** e2e run with Groq key removed mid-run — utterances keep transcribing locally.

## Phase C — Wayland input (keyboard first)

### C1. Input backend seam inside the gnome adapter
- **Tests:** `tests/adapters/` — backend selection by `XDG_SESSION_TYPE`/`WAYLAND_DISPLAY`
  (mirror `gnome_clipboard_provider` logic); X11 backend delegates to today's xdotool path
  unchanged.
- **Change:** new package `adapters/gnome/input_backends/` (ABC + `x11_backend.py` +
  `portal_backend.py` — ≥3 cohesive files); `gnome_input_simulator.py` becomes selection +
  delegation.

### C2. Portal RemoteDesktop client — keyboard/typing
- **Tests:** unit with a fake D-Bus connection: session create → `SelectDevices(keyboard)`
  → `Start` → keycode notify sequence for `type_text`/`press_keys`; `restore_token`
  persisted to `.tusk_runtime/` and reused (no repeat consent dialog).
- **Change:** portal client + evdev keycode map in `input_backends/` (`dbus-next` in the
  gnome adapter's `requirements.txt` — venv-isolated, not in the kernel image). D-Bus
  session bus is already mounted in compose.
- **Verify:** on a Wayland session: dictation into gnome-text-editor (native Wayland
  window — xdotool cannot do this today). X11 regression: existing e2e unchanged.

### C3. Pointer — deferred, documented
Absolute pointer motion via portal requires pairing a ScreenCast stream. Park it: document
mouse tools as X11/XWayland-only for now; revisit with the extension (D2) which can click
natively. One paragraph in README + tool descriptions updated so the planner knows.

## Phase D — Wayland windows + context

### D1. GNOME Shell extension
- **Change:** new top-level `shell-extension/` (sibling of `launcher/` — same host-side
  pattern): thin D-Bus service `org.tusk.WindowControl` — ListWindows, FocusWindow,
  MoveResize, Close, Minimize/Maximize, ActiveWindow. Dumb by design: no logic beyond
  Meta/Shell calls, minimizing GNOME-version coupling. Manual install documented like the
  AppIndicator prerequisite.
- **Tests:** JS kept trivial; contract tested from the Python side against a fake bus.

### D2. Window + context backends
- **Tests:** window tools and `gnome_context_provider` select wmctrl vs D-Bus backend by
  session type; extension absent on Wayland → tools return failed `ToolResult` with an
  actionable message ("install the TUSK shell extension"), context falls back to empty.
- **Change:** backend pair for `window_tools.py` + `gnome_context_provider.py` (same
  selection helper as C1 — extract once, reuse).
- **Verify:** Wayland session with extension: "focus firefox, maximize it" e2e; without
  extension: graceful message, no crash.

## Acceptance criteria
- Kill any adapter process → auto-recovery, no restart, user informed via status.
- Unplug/replug mic → listening resumes without restart.
- Dictation + coding modes fully functional on a native Wayland GNOME session (C2).
- Window management on Wayland with the extension; graceful degradation without.

## Out of scope
- ydotool/uinput path (portal chosen); non-GNOME compositors; pointer on Wayland (C3);
  automated GNOME-version CI matrix (manual checklist per GNOME release instead).

## Risks
- Portal dialects vary by distro/version — validate on Ubuntu GNOME (the dev machine)
  first, keep the backend probe-then-fallback (portal init failure → X11/XWayland path +
  status warning, never a crash).
- Supervisor/watcher interaction — single-owner rule above; add one integration test
  covering "manifest edited while adapter down".
