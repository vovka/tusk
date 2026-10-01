import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import St from 'gi://St';

const MODIFIERS = {ctrl: 'Control_L', control: 'Control_L', alt: 'Alt_L', shift: 'Shift_L', super: 'Super_L'};
const CHAR_KEYS = {'\n': Clutter.KEY_Return, '\b': Clutter.KEY_BackSpace, '\t': Clutter.KEY_Tab};
const now = () => GLib.get_monotonic_time();

function windows() {
    return global.get_window_actors().map(actor => actor.meta_window)
        .filter(win => win.get_window_type() === Meta.WindowType.NORMAL);
}

function findWindow(id) {
    const win = windows().find(candidate => candidate.get_id() === id);
    if (!win) throw new Error(`no window with id ${id}`);
    return win;
}

function keyval(name) {
    const key = MODIFIERS[name.toLowerCase()] ?? name;
    if ([...key].length === 1)
        return Clutter.unicode_to_keysym(key.codePointAt(0));
    const value = Clutter[`KEY_${key}`];
    if (value === undefined) throw new Error(`unknown key ${name}`);
    return value;
}

function tile(win, left) {
    const area = win.get_work_area_current_monitor();
    const width = Math.floor(area.width / 2);
    win.unmaximize(Meta.MaximizeFlags.BOTH);
    win.move_resize_frame(true, left ? area.x : area.x + width, area.y, width, area.height);
}

export class ShellService {
    constructor(keyboard, pointer) {
        this._keyboard = keyboard;
        this._pointer = pointer;
    }

    ListWindows() {
        const focus = global.display.get_focus_window();
        return JSON.stringify(windows().map(win => {
            const rect = win.get_frame_rect();
            return {id: win.get_id(), title: win.get_title() ?? '', wm_class: win.get_wm_class() ?? '',
                focused: win === focus, x: rect.x, y: rect.y, width: rect.width, height: rect.height};
        }));
    }

    Focus(id) { findWindow(id).activate(global.get_current_time()); }
    Close(id) { findWindow(id).delete(global.get_current_time()); }
    Maximize(id) { findWindow(id).maximize(Meta.MaximizeFlags.BOTH); }
    Minimize(id) { findWindow(id).minimize(); }

    MoveResize(id, x, y, width, height) {
        const win = findWindow(id);
        win.unmaximize(Meta.MaximizeFlags.BOTH);
        win.move_resize_frame(true, x, y, width, height);
    }

    TileLeft(id) { tile(findWindow(id), true); }
    TileRight(id) { tile(findWindow(id), false); }

    SwitchWorkspace(index) {
        global.workspace_manager.get_workspace_by_index(index).activate(global.get_current_time());
    }

    KeyCombo(names) {
        const keys = names.map(keyval);
        keys.forEach(key => this._keyboard.notify_keyval(now(), key, Clutter.KeyState.PRESSED));
        keys.reverse().forEach(key => this._keyboard.notify_keyval(now(), key, Clutter.KeyState.RELEASED));
    }

    TypeText(text) {
        // Mutter can only type keyvals in the active layout, so non-ASCII runs are pasted
        // through the clipboard (which they overwrite) with ctrl+v.
        for (const run of text.match(/[\x00-\x7f]+|[^\x00-\x7f]+/gu) ?? []) {
            if (/^[\x00-\x7f]/.test(run))
                [...run].forEach(char => this._tap(CHAR_KEYS[char] ?? Clutter.unicode_to_keysym(char.codePointAt(0))));
            else
                this._paste(run);
        }
    }

    _tap(key) {
        this._keyboard.notify_keyval(now(), key, Clutter.KeyState.PRESSED);
        this._keyboard.notify_keyval(now(), key, Clutter.KeyState.RELEASED);
    }

    _paste(text) {
        St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text);
        this.KeyCombo(['ctrl', 'v']);
    }

    PointerMove(x, y) { this._pointer.notify_absolute_motion(now(), x, y); }

    PointerButton(button, pressed) {
        this._pointer.notify_button(now(), button, pressed ? Clutter.ButtonState.PRESSED : Clutter.ButtonState.RELEASED);
    }

    Scroll(down, clicks) {
        const direction = down ? Clutter.ScrollDirection.DOWN : Clutter.ScrollDirection.UP;
        for (let i = 0; i < clicks; i++)
            this._pointer.notify_discrete_scroll(now(), direction, Clutter.ScrollSource.WHEEL);
    }
}
