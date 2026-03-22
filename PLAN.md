# Plan: Add General Agent Tools (Input, Window, Clipboard, Mouse, Desktop)

## Summary

Add 14 new tools to TUSK's agent, organized in 5 categories. All xdotool/wmctrl-based.
An `InputSimulator` ABC abstracts low-level input so tools stay testable and platform-swappable.

---

## Step 0 — New interface: `InputSimulator`

Several tools need `xdotool` for keys, typing, and mouse. Currently `GnomeTextPaster`
already wraps xdotool for typing. Extract a broader abstraction.

**New file: `tusk/interfaces/input_simulator.py`**
- ABC with methods: `press_keys`, `type_text`, `mouse_click`, `mouse_move`,
  `mouse_drag`, `mouse_scroll`
- Each method has typed parameters (no `*args/**kwargs`)

**New file: `tusk/gnome/gnome_input_simulator.py`**
- Concrete implementation using `xdotool` subprocess calls
- `press_keys(keys: str)` → `xdotool key <keys>`
- `type_text(text: str)` → `xdotool type --delay 0 -- <text>`
- `mouse_click(x: int, y: int, button: int, clicks: int)` → `xdotool mousemove x y && xdotool click --repeat N button`
- `mouse_move(x: int, y: int)` → `xdotool mousemove x y`
- `mouse_drag(from_x: int, from_y: int, to_x: int, to_y: int, button: int)` → move, mousedown, move, mouseup
- `mouse_scroll(direction: str, clicks: int)` → `xdotool click 4/5` (up/down)

Update `interfaces/__init__.py` to export `InputSimulator`.

---

## Step 1 — Input Simulation Tools

**New file: `tusk/gnome/tools/press_keys_tool.py`**
- Injects `InputSimulator`
- parameter: `{"keys": "<key_combination>"}`
- Delegates to `simulator.press_keys(keys)`
- Examples: `ctrl+a`, `Delete`, `ctrl+shift+t`

**New file: `tusk/gnome/tools/type_text_tool.py`**
- Injects `InputSimulator`
- parameter: `{"text": "<text_to_type>"}`
- Delegates to `simulator.type_text(text)`

---

## Step 2 — Window Management Tools

**New file: `tusk/gnome/tools/focus_window_tool.py`**
- parameter: `{"window_title": "<title>"}`
- Uses `wmctrl -a <title>` to activate/focus

**New file: `tusk/gnome/tools/maximize_window_tool.py`**
- parameter: `{"window_title": "<title>"}`
- Uses `wmctrl -r <title> -b add,maximized_vert,maximized_horz`

**New file: `tusk/gnome/tools/minimize_window_tool.py`**
- parameter: `{"window_title": "<title>"}`
- Uses `xdotool` search + windowminimize

**New file: `tusk/gnome/tools/move_resize_window_tool.py`**
- parameters: `{"window_title": "<title>", "geometry": "<x>,<y>,<w>,<h>"}`
- Uses `wmctrl -r <title> -e 0,x,y,w,h`
- Covers both move and resize in one tool (they're the same wmctrl call)

---

## Step 3 — Mouse Tools

**New file: `tusk/gnome/tools/mouse_click_tool.py`**
- Injects `InputSimulator`
- parameters: `{"x": "<x>", "y": "<y>", "button": "<left|right|middle>", "clicks": "<1|2|3>"}`
- `button` and `clicks` default to "left" and "1" in execute logic

**New file: `tusk/gnome/tools/mouse_move_tool.py`**
- Injects `InputSimulator`
- parameters: `{"x": "<x>", "y": "<y>"}`

**New file: `tusk/gnome/tools/mouse_drag_tool.py`**
- Injects `InputSimulator`
- parameters: `{"from_x": "<x>", "from_y": "<y>", "to_x": "<x>", "to_y": "<y>"}`

**New file: `tusk/gnome/tools/mouse_scroll_tool.py`**
- Injects `InputSimulator`
- parameters: `{"direction": "<up|down>", "clicks": "<amount>"}`

---

## Step 4 — Clipboard Tools

**New file: `tusk/interfaces/clipboard_provider.py`**
- ABC with `read() -> str` and `write(text: str) -> None`

**New file: `tusk/gnome/gnome_clipboard_provider.py`**
- Uses `xclip -selection clipboard -o` for read
- Uses `xclip -selection clipboard` with stdin for write

**New file: `tusk/gnome/tools/read_clipboard_tool.py`**
- Injects `ClipboardProvider`
- parameters: `{}` (none)
- Returns clipboard contents in `ToolResult.message`

**New file: `tusk/gnome/tools/write_clipboard_tool.py`**
- Injects `ClipboardProvider`
- parameters: `{"text": "<text>"}`

Update `interfaces/__init__.py` to export `ClipboardProvider`.

---

## Step 5 — Desktop Navigation Tools

**New file: `tusk/gnome/tools/open_uri_tool.py`**
- parameters: `{"uri": "<url_or_path>"}`
- Uses `xdg-open <uri>`

**New file: `tusk/gnome/tools/switch_workspace_tool.py`**
- parameters: `{"workspace_number": "<n>"}`
- Uses `wmctrl -s <n>`

---

## Step 6 — Registration in `main.py`

Update `_build_tool_registry` to accept `InputSimulator` and `ClipboardProvider`,
create all new tools via DI, and register them.

Update `main()`:
- Instantiate `GnomeInputSimulator`
- Instantiate `GnomeClipboardProvider`
- Pass both to `_build_tool_registry`

---

## Step 7 — Update `__init__.py` exports

- `tusk/gnome/tools/__init__.py` — add all 14 new tool classes to `__all__`
- `tusk/interfaces/__init__.py` — add `InputSimulator`, `ClipboardProvider`

---

## File count summary

| Category | New files | Location |
|----------|-----------|----------|
| Interfaces | 2 | `tusk/interfaces/` |
| GNOME impls | 2 | `tusk/gnome/` |
| Input tools | 2 | `tusk/gnome/tools/` |
| Window tools | 4 | `tusk/gnome/tools/` |
| Mouse tools | 4 | `tusk/gnome/tools/` |
| Clipboard tools | 2 | `tusk/gnome/tools/` |
| Desktop tools | 2 | `tusk/gnome/tools/` |
| **Total new** | **18** | |
| Modified | 3 | `main.py`, 2x `__init__.py` |

---

## Notes

- `GnomeTextPaster` stays as-is — it's used by dictation mode for continuous typing with replace logic. `InputSimulator` is a broader, separate concern.
- All tools follow the existing pattern: implement `AgentTool`, one class per file, < 100 lines, < 10 lines per method.
- Mouse tools will be limited without vision/screenshot capability, but still useful for coordinate-based commands and scripted flows.
- No changes to core (agent, registry, pipeline) — tools are purely additive via registry.
