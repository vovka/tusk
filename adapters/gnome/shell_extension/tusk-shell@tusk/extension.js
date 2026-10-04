import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import {ShellService} from './shell_service.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

// Input argument signatures per method; ListWindows alone returns a JSON string.
const METHODS = {
    Focus: ['t'], Close: ['t'], Maximize: ['t'], Minimize: ['t'], MoveResize: ['t', 'i', 'i', 'i', 'i'],
    SwitchWorkspace: ['i'], KeyCombo: ['as'], TypeText: ['s'], PointerMove: ['i', 'i'],
    PointerButton: ['u', 'b'], Scroll: ['b', 'u'], TileLeft: ['t'], TileRight: ['t'],
};
const inArgs = types => types.map(type => `<arg type="${type}" direction="in"/>`).join('');
const IFACE = `<node><interface name="org.tusk.Shell">
  <method name="ListWindows"><arg type="s" direction="out"/></method>
  ${Object.entries(METHODS).map(([name, types]) => `<method name="${name}">${inArgs(types)}</method>`).join('')}
</interface></node>`;

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
        // KeyCombo/TypeText release every key they press within the same call, so nothing is held here.
        this._keyboard.run_dispose();
        this._pointer.run_dispose();
        this._exported = this._keyboard = this._pointer = null;
    }
}
