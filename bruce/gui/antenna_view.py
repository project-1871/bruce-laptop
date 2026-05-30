import threading
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from bruce.gui.tool_view import ToolView
from bruce.core.iface import (
    get_wifi_interfaces, get_adapter_info,
    set_tx_power, set_tx_power_auto,
    set_monitor_mode, set_managed_mode,
    detect_cc1101, detect_pn532, detect_nrf24, detect_si4713,
)


class AntennaManagerView(ToolView):
    def __init__(self):
        self._ifaces = get_wifi_interfaces() or ["wlan0"]
        self._iface_combo = Gtk.DropDown.new_from_strings(self._ifaces)
        self._tx_entry = Gtk.Entry()
        self._tx_entry.set_text("20")
        self._tx_entry.set_max_width_chars(6)
        self._tx_entry.set_width_chars(6)
        super().__init__("Antenna Manager")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)

        lbl = Gtk.Label(label="Adapter")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._iface_combo)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        bar.append(sep)

        lbl2 = Gtk.Label(label="TX Power (dBm)")
        lbl2.add_css_class("field-label")
        bar.append(lbl2)
        bar.append(self._tx_entry)

        btn_set = Gtk.Button(label="Set")
        btn_set.add_css_class("btn-action")
        btn_set.connect("clicked", self._on_set_tx)
        bar.append(btn_set)

        btn_max = Gtk.Button(label="Auto/Max")
        btn_max.add_css_class("btn-action")
        btn_max.connect("clicked", self._on_auto_tx)
        bar.append(btn_max)

        return bar

    def build_bottom_controls(self, bar: Gtk.Box):
        btn_mon = Gtk.Button(label="Set Monitor")
        btn_mon.add_css_class("btn-action")
        btn_mon.connect("clicked", self._on_monitor)
        bar.append(btn_mon)

        btn_mng = Gtk.Button(label="Set Managed")
        btn_mng.add_css_class("btn-action")
        btn_mng.connect("clicked", self._on_managed)
        bar.append(btn_mng)

    def _selected_iface(self) -> str:
        ifaces = get_wifi_interfaces() or self._ifaces
        idx = self._iface_combo.get_selected()
        return ifaces[idx] if idx < len(ifaces) else ifaces[0]

    def _on_set_tx(self, _btn):
        iface = self._selected_iface()
        try:
            dbm = float(self._tx_entry.get_text().strip())
        except ValueError:
            GLib.idle_add(self.output.append, "Invalid dBm value", "red")
            return
        threading.Thread(target=self._do_tx, args=(iface, dbm), daemon=True).start()

    def _do_tx(self, iface, dbm):
        ok, msg = set_tx_power(iface, dbm)
        GLib.idle_add(self.output.append, msg, "orange" if ok else "red")

    def _on_auto_tx(self, _btn):
        iface = self._selected_iface()
        threading.Thread(target=self._do_auto_tx, args=(iface,), daemon=True).start()

    def _do_auto_tx(self, iface):
        ok, msg = set_tx_power_auto(iface)
        GLib.idle_add(self.output.append, msg, "orange" if ok else "red")

    def _on_monitor(self, _btn):
        iface = self._selected_iface()
        threading.Thread(target=self._do_monitor, args=(iface,), daemon=True).start()

    def _do_monitor(self, iface):
        ok, msg = set_monitor_mode(iface)
        GLib.idle_add(self.output.append, msg, "orange" if ok else "red")

    def _on_managed(self, _btn):
        iface = self._selected_iface()
        threading.Thread(target=self._do_managed, args=(iface,), daemon=True).start()

    def _do_managed(self, iface):
        ok, msg = set_managed_mode(iface)
        GLib.idle_add(self.output.append, msg, "orange" if ok else "red")

    def run_tool(self):
        ifaces = get_wifi_interfaces()
        if not ifaces:
            self.log("No WiFi interfaces found.", "red")
        else:
            self.log("── WiFi Adapters ──", "orange")
            for iface in ifaces:
                info = get_adapter_info(iface)
                self.log(f"  {iface}", "amber")
                self.log(f"    PHY:      {info['phy']}")
                self.log(f"    Driver:   {info['chipset']}")
                self.log(f"    Bands:    {', '.join(info['bands']) or 'unknown'}")
                self.log(f"    Mode:     {info['mode']}")
                mon = "✓ yes" if info["monitor"] else "○ no"
                inj = "✓ yes" if info["injection"] else "○ no"
                self.log(f"    Monitor:  {mon}", "orange" if info["monitor"] else "dim")
                self.log(f"    Injection:{inj}", "orange" if info["injection"] else "dim")
                tx = info["tx_power_dbm"]
                self.log(f"    TX Power: {f'{tx:.2f} dBm' if tx is not None else 'unknown'}")
                self.log("")

        self.log("── Hardware Modules ──", "orange")
        modules = [
            ("CC1101 (SubGHz)",  detect_cc1101()),
            ("PN532 (NFC/RFID)", detect_pn532()),
            ("NRF24L01 (2.4GHz)", detect_nrf24()),
            ("Si4713 (FM TX)",   detect_si4713()),
        ]
        for name, found in modules:
            tag = "orange" if found else "dim"
            mark = "✓" if found else "○"
            self.log(f"  {mark} {name}", tag)
        self.log("")
        self.log("── TX Power Notes ──", "dim")
        self.log("  Max legal TX power varies by country/regulatory domain.", "dim")
        self.log("  'Auto/Max' removes fixed limit — driver uses regulatory max.", "dim")
        self.log("  Monitor mode required for packet injection.", "dim")
