import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

// Input argument signatures per method; ListWindows alone returns a JSON string.
const METHODS = {
    Focus: ['t'], Close: ['t'], Maximize: ['t'], Minimize: ['t'], MoveResize: ['t', 'i', 'i', 'i', 'i'],
    SwitchWorkspace: ['i'], KeyCombo: ['as'], TypeText: ['s'], PointerMove: ['i', 'i'],
    PointerButton: ['u', 'b'], Scroll: ['b', 'u'],
};
const inArgs = types => types.map(type => `<arg type="${type}" direction="in"/>`).join('');
const IFACE = `<node><interface name="org.tusk.Shell">
  <method name="ListWindows"><arg type="s" direction="out"/></method>
  ${Object.entries(METHODS).map(([name, types]) => `<method name="${name}">${inArgs(types)}</method>`).join('')}
</interface></node>`;

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

class ShellService {
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

    SwitchWorkspace(index) {
        global.workspace_manager.get_workspace_by_index(index).activate(global.get_current_time());
    }

    KeyCombo(names) {
        const keys = names.map(keyval);
        keys.forEach(key => this._keyboard.notify_keyval(now(), key, Clutter.KeyState.PRESSED));
        keys.reverse().forEach(key => this._keyboard.notify_keyval(now(), key, Clutter.KeyState.RELEASED));
    }

    TypeText(text) {
        for (const char of text) {
            const key = CHAR_KEYS[char] ?? Clutter.unicode_to_keysym(char.codePointAt(0));
            this._keyboard.notify_keyval(now(), key, Clutter.KeyState.PRESSED);
            this._keyboard.notify_keyval(now(), key, Clutter.KeyState.RELEASED);
        }
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

export default class TuskShellExtension extends Extension {
    enable() {
        const seat = Clutter.get_default_backend().get_default_seat();
        this._keyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
        this._pointer = seat.create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
        const service = new ShellService(this._keyboard, this._pointer);
        this._exported = Gio.DBusExportedObject.wrapJSObject(IFACE, service);
        this._exported.export(Gio.DBus.session, '/org/tusk/Shell');
        this._nameId = Gio.bus_own_name_on_connection(Gio.DBus.session, 'org.tusk.Shell',
            Gio.BusNameOwnerFlags.NONE, null, null);
    }

    disable() {
        Gio.bus_unown_name(this._nameId);
        this._exported.unexport();
        this._exported = this._keyboard = this._pointer = null;
    }
}
