# Direction: Reliability & Wayland-Native Input

**Research basis:** the single most repeated pain across communities — assistive/voice
stacks that "break after OS updates", dead mics, fragile engines
([market research](../../market-research-reddit-2026-07.md)). VoiceAttack-after-Windows-update
is the cautionary tale; the winner is "OS-resilient" with health checks and self-healing.
**Verdict:** the architecture isolates every fragile piece behind a seam, so this is
implementation work plus one genuinely new host-side component (Wayland bridge). The
kernel and shells don't change shape; `AdapterManager` gains a supervision responsibility.
This direction hardens the **first reference platform** (GNOME on Linux) and establishes
the platform-backend pattern — TUSK's core is OS-agnostic, and future desktop
environments/OSes reuse these seams as new adapters rather than new architecture.

**Diagram:** [Wayland backends & host bridge](wayland-backends.md) · **Plan:** [PLAN.md](PLAN.md)

## What the architecture already provides

- **Display-server code is quarantined.** All `wmctrl`/`xdotool`/`xclip` usage lives in
  `adapters/gnome/tools/` handler classes (invariant: "tools are the only place
  platform-specific execution logic lives"). A Wayland backend replaces providers inside one
  adapter, invisible to the kernel.
- **Dual-path precedent.** `gnome_clipboard_provider.py` already selects `wl-clipboard` vs
  `xclip` by session type — the exact pattern input/window providers need.
- **Host-side escape hatch exists.** The launcher daemon (Unix socket, host user) is the
  template for anything the container can't do: a GNOME Shell D-Bus bridge or portal client
  is a second client of the same pattern.
- **Degradation machinery exists.** `LLMRetryRunner` (3 attempts, interrupt-aware),
  `AGENT_BACKEND_FALLBACK`, adapter startup retry with managed venv, tray degrading to
  headless, `StatusReporterHub` + `StatusSnapshot.mic` for surfacing health.
- **Hot-plug watcher.** `AdapterManager.start_watcher()` already reacts to manifest changes.

## Gaps

- **Wayland input:** `xdotool` drives only XWayland windows. Native paths are `ydotool`
  (uinput; host daemon + permissions) or the `org.freedesktop.portal.RemoteDesktop` API
  (one-time user consent dialog).
- **Wayland window management:** no wire protocol exists; on GNOME it requires a Shell
  extension exposing list/focus/move/resize over D-Bus — a new host-side component.
- **No runtime adapter supervision.** Startup-only: a crashed adapter process leaves dead
  `MCPToolProxy` entries; the watcher watches manifests, not process death. No liveness
  polling loop, no restart — though the building blocks exist
  (`MCPClient.is_running`, `ToolRegistry.unregister_source`,
  `AdapterManager.stop_adapter`/`start_adapter`; see PLAN-DETAILS corrections).
- **Mic loss is fatal.** Per the error-handling table, `AudioCapture` propagates
  `PortAudioError` and crashes the process — a PipeWire restart or USB mic unplug kills TUSK.
- **No STT fallback.** A Groq outage degrades every utterance; local `WhisperSTT` exists but
  is never used as a fallback (e2e baseline flakiness is exactly this — provider timeouts).

## Required changes

1. **[adapters/gnome]** Session-type provider selection for input and windows, mirroring the
   clipboard pattern: `InputSimulator`/`WindowBackend` interface pairs with X11 and Wayland
   implementations chosen at server start.
2. **[new, host]** Wayland bridge: portal `RemoteDesktop` client for input (preferred — stable
   API, no shell-version coupling) and a minimal GNOME Shell extension for window management,
   both spoken to via launcher-style socket/D-Bus from the gnome adapter.
3. **[kernel]** `AdapterManager` supervision: poll child liveness, restart with backoff,
   re-run handshake + `tools/list`, swap registry entries; mark tools unavailable (failed
   `ToolResult`, status surface) while down.
4. **[shells/voice]** `AudioCapture` recovery: catch `PortAudioError`, reopen the stream with
   backoff, report through the existing mic status field instead of crashing.
5. **[providers/stt]** `STT_ENGINE_FALLBACK` (e.g. `whisper`): on repeated primary-engine
   failure, transcribe via the fallback — mirrors the agent-backend fallback design.

## Risks & notes

- A GNOME Shell extension is itself version-coupled — the "breaks after OS updates" trap.
  Mitigation: keep it dumb (thin D-Bus over `global.get_window_actors()`), prefer portals
  wherever they cover the need, and treat the extension as optional (window tools degrade,
  input keeps working).
- Portals are the OS-agnostic choice on purpose: `org.freedesktop.portal.RemoteDesktop`
  is implemented by GNOME, KDE, and wlroots portal backends alike, so the input path
  built here serves other desktop environments unchanged; only window control needs
  per-DE backends later.
- `ydotool` needs `/dev/uinput` permissions — worse install friction than the portal consent
  dialog; portal-first is the lazy correct order.
- Supervision must not fight the hot-plug watcher; restart logic belongs in one place.
