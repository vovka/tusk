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
`TileLeft/TileRight(t id)` (unmaximize, then half of the monitor work area),
`SwitchWorkspace(i)`, `KeyCombo(as)` (keysym names such as `Return`, single characters, or
`ctrl/alt/shift/super`), `TypeText(s)` (`\n` -> Return, `\b` -> BackSpace, `\t` -> Tab; non-ASCII runs are pasted via
the clipboard + Ctrl+V because Mutter only types keyvals of the active layout),
`PointerMove(i x, i y)` (absolute), `PointerButton(u button, b pressed)`, `Scroll(b down, u clicks)`.
Unknown window ids or key names fail with a D-Bus error. Window ids are `t` because Mutter ids
exceed 2^31. `ActiveWindow` from the first draft was dropped: the focused flag in
`ListWindows` covers it (and `get_active_window`).

## Key files

- `adapters/gnome/shell_extension/tusk-shell@tusk/` — the extension (`extension.js` exports the
  D-Bus object, `shell_service.js` implements the methods, `metadata.json`).
- `tile_window` (window_title, side left|right) exists on both backends; X11 unmaximizes with
  `wmctrl` and moves to half of `xdotool getdisplaygeometry` (whole screen, ignores panels).
- `scripts/install-gnome-extension.sh` — symlinks it into `~/.local/share/gnome-shell/extensions`
  and enables it; on Wayland it loads only after logging out and in.
- `adapters/gnome/wayland/` — `ShellBus` (`gdbus call` wrapper; arguments are JSON, which is valid
  GVariant text), `WaylandInputSimulator` and `WaylandWindowTools` (subclass the X11 classes to
  reuse key normalisation and geometry parsing), `WaylandTextPaster`, `WaylandContextProvider`.
- `server.py` alone picks the backend: it passes `GnomeToolRouter` the window tools and the window
  lister (X11: `WindowTools` + `X11Windows` from `adapters/gnome/x11/`; Wayland: one `WaylandWindowTools` for both).
- `docker-compose.yml` passes `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR` and mounts
  the Wayland socket (`/dev/null` stands in on X11 hosts). `apparmor=unconfined` lives in the opt-in
  `docker-compose.wayland.yml`: the host dbus-daemon rejects clients confined by Docker's default
  AppArmor profile (`scripts/host_bus_check.sh` shows both cases). Absolute `WAYLAND_DISPLAY` is unsupported.
- Window titles resolve to one id: exact case-insensitive match first, else a unique substring;
  several matches fail with the candidate list. X11 then acts by id (`wmctrl -i`).

## Pitfalls

- Each `ShellBus` call spawns `gdbus` (~10 ms); a mouse click with N clicks is 1 + 2N calls.
- Any process on the session bus can call `org.tusk.Shell` and inject input, like `xdotool` on X11.
- Non-ASCII text overwrites the clipboard and relies on Ctrl+V (fails in terminals).
- Input goes to whatever has focus; if the Activities overview is open it receives the keys.

## Plan and verification

1. Extension + install script (`scripts/install-gnome-extension.sh`).
2. Wayland adapter classes with unit tests mirroring `tests/adapters/test_gnome_*`.
3. Docker/compose: Wayland socket and session bus are reachable; X11 mounts kept.
4. End-to-end (evidence in `docs/features/wayland-e2e/`, all scripts rerunnable):
   - `scripts/wayland_e2e.sh`: headless `gnome-shell --wayland` on a private dbus-daemon and temp
     HOME; the host launcher runs on a private socket (module constant overridden) so
     `launch_application` opens gedit in the nested shell; `scripts/e2e_driver.py wayland` runs in the
     Docker image and uses only `GnomeToolRouter.call` (`wayland_tool_calls.log`, screenshots).
     Screenshots go through `scripts/shell_screenshot.py`, which owns `org.gnome.Screenshot`
     (GNOME allow-lists it). Results: launch detected the new window; typed
     "Hello from Tusk on Wayland\nПривіт" read back exactly (clipboard and saved file); tile left
     640x768 at 0,32; maximize 1280x768; maximize then tile right 640x768 at 640,32 (no snap-back);
     two gedit windows -> ambiguity error; close by exact title.
   - `scripts/x11_e2e.sh`: Xvfb :99 + openbox + two xterms in a disposable container
     (`x11_tool_calls.log`, `x11_*.png`).
   - `scripts/host_bus_check.sh`, `scripts/install_extension_check.sh`: see their logs.
5. README "Display server support" and setup steps (done).
