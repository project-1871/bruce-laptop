import sys
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib
from bruce.core.state import STATE

ASSETS = Path(__file__).parent.parent.parent / "assets"


class ModeDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Bruce — Select Mode", transient_for=parent, modal=True)
        self.set_default_size(480, 300)
        self.selected_mode = None

        content = self.get_content_area()
        content.set_spacing(16)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(24)
        content.set_margin_bottom(16)

        title = Gtk.Label()
        title.set_markup('<span font_family="monospace" foreground="#ff8800" size="large" weight="bold">Select Operating Mode</span>')
        content.append(title)

        sub = Gtk.Label(label="Your choice is saved and can be changed in Settings.")
        sub.add_css_class("section-subtext")
        content.append(sub)

        off_btn = Gtk.Button()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        v1 = Gtk.Label()
        v1.set_markup('<span font_family="monospace" foreground="#ff4444" weight="bold">OFFENSIVE</span>')
        v2 = Gtk.Label(label="Full toolkit — all attack tools enabled")
        v2.add_css_class("section-subtext")
        vbox.append(v1)
        vbox.append(v2)
        off_btn.set_child(vbox)
        off_btn.add_css_class("tool-card")
        off_btn.connect("clicked", self._select, "OFFENSIVE")
        content.append(off_btn)

        mon_btn = Gtk.Button()
        mvbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        m1 = Gtk.Label()
        m1.set_markup('<span font_family="monospace" foreground="#ffaa00" weight="bold">MONITOR</span>')
        m2 = Gtk.Label(label="Passive / defensive tools only")
        m2.add_css_class("section-subtext")
        mvbox.append(m1)
        mvbox.append(m2)
        mon_btn.set_child(mvbox)
        mon_btn.add_css_class("tool-card")
        mon_btn.connect("clicked", self._select, "MONITOR")
        content.append(mon_btn)

    def _select(self, _btn, mode: str):
        self.selected_mode = mode
        self.close()


class BruceGtkApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.bruce.laptop",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app):
        from bruce.gui.window import BruceWindow
        if STATE.mode is None:
            tmp = Gtk.Window(application=self)
            tmp.hide()
            dialog = ModeDialog(tmp)
            dialog.connect("close-request", self._on_mode_selected, dialog, tmp)
            tmp.present()
            dialog.present()
        else:
            win = BruceWindow(self)
            win.present()

    def _on_mode_selected(self, _dialog, dialog, tmp):
        if dialog.selected_mode:
            STATE.mode = dialog.selected_mode
        tmp.close()
        from bruce.gui.window import BruceWindow
        win = BruceWindow(self)
        win.present()


def run() -> int:
    app = BruceGtkApp()
    return app.run(None)
