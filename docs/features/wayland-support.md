# Wayland support (GNOME)

Last updated: 2026-10-01

## Goal

The GNOME adapter drives a native GNOME Wayland session (input, windows, app launch
detection, desktop context) without X11. The X11 path (`xdotool`/`wmctrl`) is unchanged.

## Decisions

- **One GNOME Shell extension for input and windows** (`tusk-shell@tusk`, GNOME 46).
  GNOME exposes no external window API on Wayland, and `org.gnome.Shell.Eval` is
  disabled, so an extension is needed for windows anyway. The same extension creates
  Clutter virtual keyboard/pointer devices for input. Spike findings:
  - RemoteDesktop portal (v2) works but shows a consent dialog, needs session/token
    handling and Request/Response plumbing. Kept as a documented fallback, not built.
  - libei has no Python binding installed and goes through the portal on GNOME anyway.
  - `ydotool`/uinput is not installed, needs `/dev/uinput` in Docker, and sends raw
    keycodes (layout-dependent).
- **D-Bus from Python via `gdbus call`** through `subprocess.run`, the same style the
  X11 code uses with `xdotool`; no new Python dependency.
- **Backend chosen at start-up** in `adapters/gnome/server.py` from
  `XDG_SESSION_TYPE=wayland` or `WAYLAND_DISPLAY`, the same rule the clipboard uses.
  Wayland classes live in `adapters/gnome/wayland/` and keep the duck-typed method
  names of the X11 classes, so the router and tools stay unchanged.
- Destructive window actions (close, maximize, move/resize, minimize) need an explicit
  window title, same as X11.

## D-Bus interface

Bus name `org.tusk.Shell`, object `/org/tusk/Shell`, interface `org.tusk.Shell`:
`ListWindows() -> s` (JSON list of `{id, title, wm_class, focused, x, y, width, height}`,
NORMAL windows only), `Focus/Close/Maximize/Minimize(t id)`, `MoveResize(t id, i x, i y, i w, i h)`,
`SwitchWorkspace(i)`, `KeyCombo(as)` (keysym names such as `Return`, single characters, or
`ctrl/alt/shift/super`), `TypeText(s)` (`\n` -> Return, `\b` -> BackSpace, `\t` -> Tab),
`PointerMove(i x, i y)` (absolute), `PointerButton(u button, b pressed)`, `Scroll(b down, u clicks)`.
Unknown window ids or key names fail with a D-Bus error. Window ids are `t` because Mutter ids
exceed 2^31. `ActiveWindow` and `TileLeft/Right` from the first draft were dropped: the
focused flag in `ListWindows` covers the former and no tool uses tiling.

## Key files

- `adapters/gnome/shell_extension/tusk-shell@tusk/` — the extension (`extension.js`, `metadata.json`).
- `scripts/install-gnome-extension.sh` — symlinks it into `~/.local/share/gnome-shell/extensions`
  and enables it; on Wayland it loads only after logging out and in.
- `adapters/gnome/wayland/` — `ShellBus` (`gdbus call` wrapper; arguments are JSON, which is valid
  GVariant text), `WaylandInputSimulator` and `WaylandWindowTools` (subclass the X11 classes to
  reuse key normalisation and geometry parsing), `WaylandTextPaster`, `WaylandContextProvider`.
- `GnomeToolRouter` takes optional `window_tools`; when it has `list_windows()`, `ApplicationTools`
  uses it (`window_lister`) to detect the launched app's window instead of `wmctrl`.
- `docker-compose.yml` passes `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR` and mounts
  the Wayland socket (on X11 hosts the missing `wayland-0` path is created as an empty directory).

## Pitfalls

- Each `ShellBus` call spawns `gdbus` (~10 ms); a mouse click with N clicks is 1 + 2N calls.
- Any process on the session bus can call `org.tusk.Shell` and inject input, like `xdotool` on X11.
- Input goes to whatever has focus; if the Activities overview is open it receives the keys.

## Plan and verification

1. Extension + install script (`scripts/install-gnome-extension.sh`).
2. Wayland adapter classes with unit tests mirroring `tests/adapters/test_gnome_*`.
3. Docker/compose: Wayland socket and session bus are reachable; X11 mounts kept.
4. End-to-end in `gnome-shell --headless --virtual-monitor 1280x800 --wayland` inside
   `dbus-run-session` with temporary HOME/XDG dirs, so the user's session is never touched.
   Verified there: ListWindows, Focus, MoveResize, Maximize, Minimize, Close, SwitchWorkspace,
   TypeText and KeyCombo (gedit title turns `*Untitled`, ctrl+n opens a second window),
   pointer click, D-Bus errors for unknown keys.
5. README "Display server support" and setup steps.
