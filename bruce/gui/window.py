from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GLib, Gio, GdkPixbuf
from bruce.core.state import STATE
from bruce.core.iface import (detect_cc1101, detect_pn532, detect_nrf24, detect_si4713,
                               get_wifi_interfaces, get_bt_interfaces)
from bruce.gui.tool_view import HardwareStubView

ASSETS = Path(__file__).parent.parent.parent / "assets"

SECTIONS = None


def _build_sections():
    from bruce.gui.wifi_views import (
        ScanAPsView, DeauthView, BeaconSpamView, RawSnifferView,
        ScanHostsView, EvilPortalView, WardrivingView, BrucegotchiView,
    )
    from bruce.gui.ble_views import (
        BLEScanView, TrackerScanView, PhantomFloodView, BLEBeaconView,
        BLEPredatorView, MediaCommandsView,
    )
    from bruce.gui.others_views import (
        QRCodeView, TimerView, SerialMonitorView, DeviceInfoView,
        ScriptsView, FilesView, WebUIView,
    )

    def stub(name, hw):
        return lambda: HardwareStubView(name, hw)

    return [
        ("wifi", "01  WiFi", [
            ("Scan APs",            ScanAPsView,    False),
            ("Deauth",              DeauthView,     False),
            ("Beacon Spam",         BeaconSpamView, False),
            ("Evil Portal",         EvilPortalView, False),
            ("RAW Sniffer / PCAP",  RawSnifferView, False),
            ("Scan Hosts",          ScanHostsView,  False),
            ("Wardriving",          WardrivingView, False),
            ("Brucegotchi",         BrucegotchiView,False),
        ]),
        ("ble", "02  BLE", [
            ("BLE Scan",            BLEScanView,        False),
            ("Tracker Scan",        TrackerScanView,    False),
            ("Phantom Flood",       PhantomFloodView,   False),
            ("BLE Beacon",          BLEBeaconView,      False),
            ("BLE Predator",        BLEPredatorView,    False),
            ("Media Commands",      MediaCommandsView,  False),
        ]),
        ("rf", "03  RF / SubGHz  [CC1101]", [
            ("Scan RF",             stub("Scan RF",             "CC1101"), True),
            ("Replay Signal",       stub("Replay Signal",       "CC1101"), True),
            ("Jammer",              stub("Jammer",              "CC1101"), True),
            ("Spectrum Analyzer",   stub("Spectrum Analyzer",   "CC1101"), True),
            ("Brute Force",         stub("Brute Force",         "CC1101"), True),
            (".Sub File Replay",    stub(".Sub File Replay",    "CC1101"), True),
        ]),
        ("rfid", "04  RFID / NFC  [PN532]", [
            ("Card Scanner",        stub("Card Scanner",    "PN532"), True),
            ("Card Reader",         stub("Card Reader",     "PN532"), True),
            ("Card Clone",          stub("Card Clone",      "PN532"), True),
            ("Key Brute Force",     stub("Key Brute Force", "PN532"), True),
            ("Card Emulate",        stub("Card Emulate",    "PN532"), True),
        ]),
        ("ir", "05  IR  [hardware]", [
            ("TV-B-Gone",           stub("TV-B-Gone",       "IR emitter (KY-005)"), True),
            ("IR Read",             stub("IR Read",         "IR receiver (KY-022)"), True),
            ("Custom IR TX",        stub("Custom IR TX",    "IR emitter (KY-005)"), True),
        ]),
        ("nrf24", "06  NRF24  [NRF24L01]", [
            ("Jam 2.4GHz",          stub("Jam 2.4GHz",        "NRF24L01+PA+LNA"), True),
            ("2.4GHz Spectrum",     stub("2.4GHz Spectrum",   "NRF24L01+PA+LNA"), True),
            ("MouseJack",           stub("MouseJack",         "NRF24L01+PA+LNA"), True),
        ]),
        ("fm", "07  FM Radio  [Si4713]", [
            ("FM Broadcast",        stub("FM Broadcast",      "Si4713 module"), True),
            ("Spectrum Analyzer",   stub("FM Spectrum",       "Si4713 module"), True),
        ]),
        ("scripts", "08  Scripts", [
            ("Script Runner",       ScriptsView,    False),
        ]),
        ("others", "09  Others", [
            ("QR Code Generator",   QRCodeView,     False),
            ("Timer",               TimerView,      False),
            ("Serial Monitor",      SerialMonitorView, False),
            ("Device Info",         DeviceInfoView, False),
        ]),
        ("files", "10  Files", [
            ("Loot Files",          FilesView,      False),
        ]),
        ("webui", "11  WebUI", [
            ("Launch WebUI",        WebUIView,      False),
        ]),
    ]


class BruceWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Bruce Laptop")
        self.set_default_size(1280, 800)
        self._sections = _build_sections()
        self._current_tool_view = None
        self._load_css()
        self._build_ui()

    def _load_css(self):
        css_file = Path(__file__).parent / "style.css"
        provider = Gtk.CssProvider()
        provider.load_from_path(str(css_file))
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        mode = STATE.mode or "OFFENSIVE"
        mode_lbl = Gtk.Label(label=f"▌ {mode}")
        mode_lbl.add_css_class("mode-banner-offensive" if mode == "OFFENSIVE" else "mode-banner-monitor")
        header.pack_start(mode_lbl)

        icon_path = ASSETS / "bruce.svg"
        if icon_path.exists():
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_size(str(icon_path), 32, 32)
                img = Gtk.Image.new_from_pixbuf(pb)
                header.pack_end(img)
            except Exception:
                pass

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(220)
        self.set_child(paned)

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_box.add_css_class("sidebar")

        logo_lbl = Gtk.Label(label="Bruce")
        logo_lbl.add_css_class("tool-view-title")
        logo_lbl.set_margin_top(12)
        logo_lbl.set_margin_bottom(8)
        sidebar_box.append(logo_lbl)
        sidebar_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        self._listbox = Gtk.ListBox()
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.add_css_class("sidebar")
        self._listbox.connect("row-activated", self._on_section_selected)

        for sec_id, label, _tools in self._sections:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=label)
            lbl.add_css_class("section-btn")
            lbl.set_xalign(0.0)
            lbl.set_margin_start(8)
            row.set_child(lbl)
            row.sec_id = sec_id
            self._listbox.append(row)

        self._listbox.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        for sec_id, label in [("settings", "12  Settings"), ("about", "13  About")]:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=label)
            lbl.add_css_class("section-btn")
            lbl.set_xalign(0.0)
            lbl.set_margin_start(8)
            row.set_child(lbl)
            row.sec_id = sec_id
            self._listbox.append(row)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(self._listbox)
        sw.set_vexpand(True)
        sidebar_box.append(sw)
        paned.set_start_child(sidebar_box)

        self._content = Gtk.Stack()
        self._content.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._content.set_hexpand(True)
        self._content.set_vexpand(True)
        paned.set_end_child(self._content)

        self._build_home()
        for sec_id, label, tools in self._sections:
            self._build_section_page(sec_id, label, tools)
        self._build_settings_page()
        self._build_about_page()
        self._content.set_visible_child_name("home")

    def _build_home(self):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_hexpand(True)
        sw.set_vexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.add_css_class("section-grid")
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        logo = Gtk.Label()
        logo.set_markup(
            '<span font_family="monospace" foreground="#ff6600" size="x-small">'
            '██████╗ ██████╗ ██╗   ██╗ ██████╗███████╗\n'
            '██╔══██╗██╔══██╗██║   ██║██╔════╝██╔════╝\n'
            '██████╔╝██████╔╝██║   ██║██║     █████╗  \n'
            '██╔══██╗██╔══██╗██║   ██║██║     ██╔══╝  \n'
            '██████╔╝██║  ██║╚██████╔╝╚██████╗███████╗\n'
            '╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝'
            '</span>'
        )
        logo.set_margin_bottom(16)
        box.append(logo)

        sub = Gtk.Label(label="Select a section from the sidebar.")
        sub.add_css_class("section-subtext")
        box.append(sub)

        sw.set_child(box)
        self._content.add_named(sw, "home")

    def _build_section_page(self, sec_id, label, tools):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        hdr = Gtk.Label(label=f"▶ {label.strip()}")
        hdr.add_css_class("section-header")
        hdr.set_xalign(0.0)
        hdr.set_margin_start(24)
        hdr.set_margin_top(20)
        hdr.set_margin_bottom(4)
        outer.append(hdr)

        sub_lbl = Gtk.Label(label=f"{len(tools)} tool{'s' if len(tools) != 1 else ''} available")
        sub_lbl.add_css_class("section-subtext")
        sub_lbl.set_xalign(0.0)
        sub_lbl.set_margin_start(24)
        sub_lbl.set_margin_bottom(12)
        outer.append(sub_lbl)

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(4)
        flow.set_min_children_per_line(1)
        flow.set_column_spacing(10)
        flow.set_row_spacing(10)
        flow.set_margin_start(24)
        flow.set_margin_end(24)
        flow.set_margin_bottom(24)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(False)

        for tool_name, tool_cls, is_stub in tools:
            btn = Gtk.Button(label=tool_name)
            btn.add_css_class("tool-card")
            if is_stub:
                btn.add_css_class("stub")
            btn.connect("clicked", self._on_tool_clicked, sec_id, tool_name, tool_cls)
            child = Gtk.FlowBoxChild()
            child.set_child(btn)
            flow.append(child)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(flow)
        sw.set_vexpand(True)
        outer.append(sw)
        self._content.add_named(outer, f"section-{sec_id}")

    def _on_section_selected(self, _lb, row):
        if not row or not hasattr(row, "sec_id"):
            return
        sid = row.sec_id
        if sid in ("settings", "about"):
            self._content.set_visible_child_name(sid)
        else:
            name = f"section-{sid}"
            if self._content.get_child_by_name(name):
                self._content.set_visible_child_name(name)

    def _on_tool_clicked(self, _btn, sec_id, tool_name, tool_cls):
        if self._current_tool_view:
            self._current_tool_view.kill_proc()
            old = self._content.get_child_by_name("tool-view")
            if old:
                self._content.remove(old)
        view = tool_cls()
        view.btn_back.connect("clicked", self._on_back_clicked, sec_id)
        self._current_tool_view = view
        self._content.add_named(view, "tool-view")
        self._content.set_visible_child_name("tool-view")

    def _on_back_clicked(self, _btn, sec_id):
        if self._current_tool_view:
            self._current_tool_view.kill_proc()
            self._current_tool_view._running = False
        self._content.set_visible_child_name(f"section-{sec_id}")

    def _build_settings_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(32)
        box.set_margin_top(24)
        box.set_margin_end(32)

        hdr = Gtk.Label(label="▶ Settings")
        hdr.add_css_class("section-header")
        hdr.set_xalign(0.0)
        box.append(hdr)

        def row(label_text, widget):
            r = Gtk.Box(spacing=16)
            lbl = Gtk.Label(label=label_text)
            lbl.add_css_class("field-label")
            lbl.set_width_chars(18)
            lbl.set_xalign(0.0)
            r.append(lbl)
            r.append(widget)
            return r

        wifi_ifaces = get_wifi_interfaces() or ["none"]
        self._wifi_combo = Gtk.DropDown.new_from_strings(wifi_ifaces)
        if STATE.wifi_iface in wifi_ifaces:
            self._wifi_combo.set_selected(wifi_ifaces.index(STATE.wifi_iface))
        box.append(row("WiFi Interface", self._wifi_combo))

        bt_ifaces = get_bt_interfaces() or ["hci0"]
        self._bt_combo = Gtk.DropDown.new_from_strings(bt_ifaces)
        box.append(row("Bluetooth Interface", self._bt_combo))

        self._mode_combo = Gtk.DropDown.new_from_strings(
            ["OFFENSIVE — Full toolkit", "MONITOR — Passive only"])
        self._mode_combo.set_selected(0 if (STATE.mode or "OFFENSIVE") == "OFFENSIVE" else 1)
        box.append(row("Mode", self._mode_combo))

        self._sudo_entry = Gtk.PasswordEntry()
        self._sudo_entry.set_show_peek_icon(True)
        self._sudo_entry.set_text(STATE.sudo_password)
        self._sudo_entry.set_hexpand(True)
        box.append(row("Sudo Password", self._sudo_entry))

        loot_lbl = Gtk.Label(label=str(STATE.loot_path))
        loot_lbl.add_css_class("status-dim")
        box.append(row("Loot Directory", loot_lbl))

        save_btn = Gtk.Button(label="Save Settings")
        save_btn.add_css_class("btn-start")
        save_btn.set_halign(Gtk.Align.START)
        save_btn.connect("clicked", self._save_settings)
        box.append(save_btn)

        self._save_status = Gtk.Label(label="")
        self._save_status.add_css_class("status-ok")
        box.append(self._save_status)

        self._content.add_named(box, "settings")

    def _save_settings(self, _btn):
        wifi_ifaces = get_wifi_interfaces() or ["none"]
        bt_ifaces = get_bt_interfaces() or ["hci0"]
        idx = self._wifi_combo.get_selected()
        if idx < len(wifi_ifaces):
            STATE.wifi_iface = wifi_ifaces[idx]
        idx = self._bt_combo.get_selected()
        if idx < len(bt_ifaces):
            STATE.config["bt_iface"] = bt_ifaces[idx]
        STATE.mode = "OFFENSIVE" if self._mode_combo.get_selected() == 0 else "MONITOR"
        STATE.sudo_password = self._sudo_entry.get_text()
        STATE.save()
        self._save_status.set_text("✓ Saved.")
        GLib.timeout_add(2000, lambda: self._save_status.set_text(""))

    def _build_about_page(self):
        from bruce.gui.tool_view import TerminalOutput
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        out = TerminalOutput()
        box.append(out)

        def populate():
            out.append("Bruce Laptop  v1.0.0", "amber")
            mode = STATE.mode or "NOT SET"
            out.append(f"Mode: {mode}", "orange" if mode == "OFFENSIVE" else "amber")
            out.append("══ Armed Modules ══", "amber")
            for iface in get_wifi_interfaces():
                out.append(f"  ✓ WiFi: {iface}", "orange")
            for iface in get_bt_interfaces():
                out.append(f"  ✓ Bluetooth: {iface}", "orange")
            hw = [
                ("CC1101 (SubGHz/RF)", detect_cc1101()),
                ("PN532 (RFID/NFC)",   detect_pn532()),
                ("NRF24L01 (2.4GHz)",  detect_nrf24()),
                ("Si4713 (FM TX)",     detect_si4713()),
            ]
            for name, present in hw:
                out.append(
                    f"  {'✓' if present else '○'} {name}",
                    "orange" if present else "dim"
                )
            out.append(f"\n  Loot: {STATE.loot_path}", "dim")

        GLib.idle_add(populate)
        self._content.add_named(box, "about")
