# Reliability & Wayland — Fine-Grained Execution Plan

Commit-by-commit detail for [PLAN.md](PLAN.md), grounded against `main` @ `3fb169d`.
Tests: `docker compose exec tusk pytest tests/kernel/ tests/shells/ tests/adapters/ tests/shared/`.

## Corrections vs. the assessment (code moved on / closer look)

- **Registry deregistration already exists** — `ToolRegistry.unregister_source(source)`
  (`tool_registry.py:14`), used by `AdapterManager.stop_adapter` (`adapter_manager.py:47`).
  Phase A step A2 collapses to nothing.
- **Liveness primitive already exists** — `MCPClient.is_running()` (`mcp_client.py:51`)
  over `transport.poll()` (`mcp_stdio_transport.py:38-39`). A1 collapses too.
- **Restart building blocks exist** — `stop_adapter(name)` + `start_adapter(dir)`
  (`adapter_manager.py:36-53`) already do deregister/shutdown and connect/register
  (including the venv-retry). The supervisor is a thin polling loop over existing methods.

## Phase A — Adapter supervision (now one commit + one small commit)

### Commit A1 — down-guard on the proxy
- **Tests:** `MCPToolProxy.execute` with a dead client returns
  `ToolResult(False, "adapter <name> unavailable")` immediately (no 30 s timeout burn);
  alive client → unchanged behavior.
- **Change:** one guard at the top of `MCPToolProxy.execute`
  (`tusk/shared/mcp/mcp_tool_proxy.py`) using the existing `client.is_running()`.

### Commit A2 — `AdapterSupervisor`
- **Tests** (fake manager recording calls, fake clock):
  - dead client detected on a poll tick → `stop_adapter` + `start_adapter` with backoff
    1 s → 2 s → 4 s … cap 30 s, retrying forever;
  - successful restart resets the backoff;
  - a healthy adapter is never touched;
  - supervisor thread survives a restart raising (logged, next tick continues);
  - `stop()` joins the thread (clean shutdown for tests).
- **Change:** new `tusk/kernel/core/adapter_supervisor.py` (~60 lines): daemon thread,
  poll interval `TUSK_ADAPTER_SUPERVISION_SECONDS` (default 5, `ConfigFactory`);
  `AdapterManager` gains two accessors it currently lacks —
  `adapter_names() -> list[str]`, `is_adapter_alive(name) -> bool`, and
  `adapter_dir(name) -> str` (manifests/clients are private dicts,
  `adapter_manager.py:23-24`). Wire + start in `startup.py`; report down/up transitions
  via the injected `StatusReporter` (detail string) and the log.
- **Boundary:** the watcher (`adapter_watcher.py`) only handles `on_created` — no overlap
  with process death. One integration test: manifest dir removed while adapter down →
  supervisor gives up on that name after `stop_adapter` (dir gone → `_manifest` returns
  `None` → logged, dropped from polling).
- **Verify live:** `docker compose exec tusk pkill -9 -f "adapters/gnome"` mid-session →
  next `gnome.*` call answers "unavailable", adapter back within backoff, no restart.

## Phase B — Audio & STT resilience

### Commit B1 — mic recovery
- **Tests** (fake `sounddevice` module injected):
  - `PortAudioError` from `stream.read` → stream closed, reopened after backoff, frames
    continue (generator never raises);
  - `PortAudioError` from `_open_stream` → retry with backoff 0.5 s → 1 s → … cap 10 s,
    forever (device may return);
  - status callback invoked on error and on recovery.
- **Change:** `shells/voice/stages/audio_capture.py` — wrap the read loop
  (`audio_capture.py:19-25`) with `except sd.PortAudioError`; extract
  `_frames_until_error` and `_backoff_delay` to hold the ≤10-line rule; optional
  `on_device_state: Callable[[bool], None]` constructor param, wired by `ShellLoader` to
  `reporter.set_microphone` (the tray already renders mic state from `StatusSnapshot`).
- **Note:** today this error crashes the process by design (error table in
  `docs/architecture.md`) — update the table row in the same commit.

### Commit B2 — STT fallback engine
- **Tests:**
  - primary raises → fallback transcribes the same utterance (result returned, failure
    logged once);
  - three consecutive primary successes after a failure → probe returns to primary
    (counter unit-tested);
  - `STT_ENGINE_FALLBACK` unset → factory returns the bare engine (zero change).
- **Change:** `tusk/providers/stt/fallback_stt.py` — `FallbackSTT(STTEngine)` wrapping
  primary+fallback (~45 lines); `STTEngineFactory.create` (`stt_engine_factory.py:13-17`)
  composes it when `config.stt_engine_fallback` is set; new key in `ConfigFactory`
  `_audio_values` (`config_factory.py:69`). Recommended default in `.env.example`:
  `STT_ENGINE_FALLBACK=whisper` (local, no key needed).
- **Latency note (hot-path rule):** fallback fires only after a primary failure — no
  added latency on the healthy path; whisper-base adds ~1–3 s per utterance *only during
  a Groq outage*. Document in the feature doc.

## Phase C — Wayland input (keyboard first)

### Commit C1 — input backend seam (pure refactor)
- **Tests:** `tests/adapters/` — existing input tests keep passing against
  `X11InputBackend`; selection helper returns `wayland` iff
  `XDG_SESSION_TYPE == "wayland"` or `WAYLAND_DISPLAY` set (same predicate as
  `gnome_clipboard_provider.py:32-33`).
- **Change:** new package `adapters/gnome/input_backends/`:
  `input_backend.py` (ABC: `press_keys`, `type_text`, `mouse_click`, `mouse_move`,
  `mouse_drag`, `mouse_scroll`), `x11_input_backend.py` (the current
  `GnomeInputSimulator` body moved verbatim — `gnome_input_simulator.py:6-75`),
  `session_detector.py` (shared predicate; `GnomeClipboardProvider` switches to it in the
  same commit — deletes its private copy). `gnome_input_simulator.py` becomes selection +
  delegation (~25 lines). gnome root stays at 8 files; the new package holds 4.

### Commit C2 — portal keyboard backend
- **Tests** (fake D-Bus connection object):
  - session bootstrap sequence: `CreateSession` → `SelectDevices(KEYBOARD)` → `Start`;
  - `restore_token` from the `Start` response persisted to
    `.tusk_runtime/portal_restore_token` and passed on the next `CreateSession` (no
    second consent dialog);
  - `type_text("hi\n")` → keysym notify calls for `h`, `i`, `Return` (reuses the newline
    rule from `gnome_input_simulator.py:41-48`);
  - `press_keys("<ctrl>s")` → modifier press, `s`, modifier release (reuse the existing
    normalizer `_normalize_keys`, `gnome_input_simulator.py:12-33` — move it to the
    package so both backends share it);
  - portal unavailable at init → backend raises; simulator falls back to X11 backend with
    a one-line warning (XWayland still covers many apps).
- **Change:** `input_backends/portal_input_backend.py` + `portal_session.py`
  (D-Bus plumbing; library decision at implementation — criteria: blocking API, no GLib
  main loop; candidates `jeepney` (pure-python) vs `dbus-next` — record the choice in
  this file). Dependency goes in `adapters/gnome/requirements.txt` (venv-isolated,
  `adapter_env_builder.py:22-31` handles install). Uses `NotifyKeyboardKeysym` (xkb
  keysyms — no layout/keycode mapping table needed for latin input; unicode →
  `0x01000000 + codepoint` rule for the rest).
- **Cross-DE note:** the portal is a freedesktop standard — this backend serves KDE and
  wlroots Wayland sessions unchanged; of the whole phase, only the D1 window extension is
  GNOME-specific.
- **Mouse on Wayland:** the four `mouse_*` methods return a failed result
  ("pointer control requires X11 on this session") — absolute pointer needs a paired
  ScreenCast stream; deferred per PLAN.md C3. Update the four tool descriptions in the
  gnome schema catalog so the *planner* knows they're X11-only.
- **Verify live:** Wayland session, `gnome-text-editor` focused (native Wayland — xdotool
  cannot reach it): dictation types a sentence; `<ctrl>s` shortcut works. X11 regression:
  existing e2e unchanged.

## Phase D — Wayland windows + context

### Commit D1 — extension
- **Change:** new top-level `shell-extension/` — `metadata.json` + `extension.js`
  exposing D-Bus `org.tusk.WindowControl` on the session bus: `ListWindows()`
  (id, title, wm_class, geometry, workspace, has_focus), `Activate(id)`,
  `MoveResize(id,x,y,w,h)`, `Close(id)`, `Minimize(id)`, `Maximize(id)`. Thin wrappers
  over `global.get_window_actors()` / `Meta.Window` — no state, no logic. Install doc
  mirrors the AppIndicator prerequisite note (`docs/architecture.md` § Notes).
- **Tests:** none in JS; the Python contract is tested in D2 against a fake bus.

### Commit D2 — window/context backends
- **Tests:** backend selection by session (same `session_detector`); on Wayland with the
  bus name absent → every window tool returns
  `ToolResult(False, "install the TUSK shell extension for window control on Wayland")`;
  context provider returns an empty-window-list `DesktopContext` instead of raising.
- **Change:** backend pair behind `adapters/gnome/tools/window_tools.py` and
  `gnome_context_provider.py` (wmctrl/xdotool vs. D-Bus calls); reuse the C2 D-Bus
  plumbing module.
- **Verify live:** Wayland + extension: "focus firefox and maximize it" e2e transcript;
  without extension: spoken failure message, no crash.

## Edge cases

| Case | Behavior |
|---|---|
| Adapter dies mid-`tools/call` | in-flight call fails via existing pipe/timeout error (`mcp_client.py:59-74`); supervisor restarts it before the next call |
| Adapter flaps (crash loop) | backoff caps at 30 s; status shows persistent down; log rate = one line per attempt |
| `kill` during sequence execution | step fails → sequence aborts with partial results (existing behavior); supervisor restores for the next turn |
| Portal consent declined by user | backend init fails → X11/XWayland fallback + warning; never re-prompts within a session |
| `restore_token` invalidated (GNOME update) | `Start` fails → delete token, one fresh consent prompt |
| Mic unplugged during TUSK speech | capture recovery is independent of playback; TTS finishes, listening resumes when a device returns |

## Explicitly not building (v1)
ydotool/uinput path; non-GNOME compositors; Wayland pointer; per-window
native-vs-XWayland backend mixing (session-level selection only); automated GNOME-version
CI matrix; adapter health metrics endpoint.

## Open items to confirm during implementation
1. D-Bus library choice for the adapter venv (jeepney vs dbus-next) — spike inside C2.
2. Whether the portal is reachable from inside the container via the mounted session bus
   (`DBUS_SESSION_BUS_ADDRESS` is already in compose) — expected yes; verify first thing
   in C2, else route through a launcher-style host helper (pattern exists).
3. Exact `sounddevice` exception classes seen on PipeWire device loss (B1 catches
   `sd.PortAudioError`; confirm nothing else leaks).
