import sys

from gi.repository import Gio, GLib

# GNOME Shell serves Screenshot only to allow-listed bus names such as org.gnome.Screenshot.
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "RequestName",
              GLib.Variant("(su)", ("org.gnome.Screenshot", 0)), None, Gio.DBusCallFlags.NONE, 5000, None)
arguments = GLib.Variant("(bbs)", (False, False, sys.argv[1]))
reply = bus.call_sync("org.gnome.Shell.Screenshot", "/org/gnome/Shell/Screenshot", "org.gnome.Shell.Screenshot",
                      "Screenshot", arguments, None, Gio.DBusCallFlags.NONE, 5000, None)
print(reply.unpack())
