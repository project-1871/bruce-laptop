import subprocess
import time
import threading
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
from bruce.gui.tool_view import ToolView, HardwareStubView
from bruce.core.state import STATE


class QRCodeView(ToolView):
    def __init__(self):
        self._text_entry = Gtk.Entry()
        self._text_entry.set_placeholder_text("Text or URL to encode")
        self._text_entry.add_css_class("field-input")
        self._text_entry.set_hexpand(True)
        self._img_box = Gtk.Box()
        super().__init__("QR Code Generator")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        lbl = Gtk.Label(label="Data")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._text_entry)
        return bar

    def run_tool(self):
        text = self._text_entry.get_text().strip()
        if not text:
            self.log("Enter text to encode.", "red")
            return
        out_path = STATE.loot_path / "qr" / "qr.png"
        self.log(f"Generating QR code for: {text}", "amber")
        try:
            import qrcode
            img = qrcode.make(text)
            img.save(str(out_path))
            self.log(f"◈ Saved to {out_path}", "amber")
            self.log(f"  Open with: eog {out_path}", "dim")
            subprocess.Popen(["eog", str(out_path)])
        except ImportError:
            self.log("qrcode not installed — pip install qrcode[pil]", "red")
        except Exception as e:
            self.log(f"Error: {e}", "red")


class TimerView(ToolView):
    def __init__(self):
        self._h_entry = Gtk.Entry()
        self._h_entry.set_text("0")
        self._h_entry.set_max_width_chars(4)
        self._h_entry.add_css_class("field-input")
        self._m_entry = Gtk.Entry()
        self._m_entry.set_text("5")
        self._m_entry.set_max_width_chars(4)
        self._m_entry.add_css_class("field-input")
        self._s_entry = Gtk.Entry()
        self._s_entry.set_text("0")
        self._s_entry.set_max_width_chars(4)
        self._s_entry.add_css_class("field-input")
        super().__init__("Timer")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=8)
        for label, widget in [("H", self._h_entry), ("M", self._m_entry), ("S", self._s_entry)]:
            l = Gtk.Label(label=label)
            l.add_css_class("field-label")
            bar.append(l)
            bar.append(widget)
        return bar

    def run_tool(self):
        try:
            total = (int(self._h_entry.get_text()) * 3600
                     + int(self._m_entry.get_text()) * 60
                     + int(self._s_entry.get_text()))
        except ValueError:
            self.log("Invalid time values.", "red")
            return
        self.log(f"Timer: {total}s", "amber")
        remaining = total
        while remaining > 0 and self._running:
            h, r = divmod(remaining, 3600)
            m, s = divmod(r, 60)
            self.log(f"  {h:02d}:{m:02d}:{s:02d}", "dim")
            time.sleep(1)
            remaining -= 1
        if remaining == 0:
            self.log("◈ TIMER COMPLETE", "amber")
            subprocess.run(["notify-send", "Bruce Timer", "Timer finished!"], capture_output=True)


class SerialMonitorView(ToolView):
    def __init__(self):
        self._port_entry = Gtk.Entry()
        self._port_entry.set_text("/dev/ttyUSB0")
        self._port_entry.add_css_class("field-input")
        self._baud_combo = Gtk.DropDown.new_from_strings(
            ["9600", "19200", "38400", "57600", "115200", "230400", "460800"])
        self._baud_combo.set_selected(4)
        self._cmd_entry = Gtk.Entry()
        self._cmd_entry.set_placeholder_text("Send command...")
        self._cmd_entry.add_css_class("field-input")
        self._cmd_entry.set_hexpand(True)
        super().__init__("Serial Monitor")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        for lbl, w in [("Port", self._port_entry), ("Baud", self._baud_combo)]:
            l = Gtk.Label(label=lbl)
            l.add_css_class("field-label")
            bar.append(l)
            bar.append(w)
        return bar

    def build_bottom_controls(self, bar: Gtk.Box):
        lbl = Gtk.Label(label="TX")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._cmd_entry)
        send_btn = Gtk.Button(label="Send")
        send_btn.add_css_class("btn-action")
        send_btn.connect("clicked", self._send_cmd)
        bar.append(send_btn)

    def _send_cmd(self, _btn):
        text = self._cmd_entry.get_text()
        if self._serial and text:
            try:
                self._serial.write((text + "\n").encode())
                self.log(f"TX: {text}", "amber")
                self._cmd_entry.set_text("")
            except Exception as e:
                self.log(f"TX error: {e}", "red")

    def run_tool(self):
        port = self._port_entry.get_text().strip()
        bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800]
        baud = bauds[self._baud_combo.get_selected()]
        self._serial = None
        try:
            import serial
            from serial.tools import list_ports
            available = [p.device for p in list_ports.comports()
                         if not p.device.startswith("/dev/ttyS")]
            self.log(f"Available ports: {available or ['none']}", "dim")
            self._serial = serial.Serial(port, baud, timeout=0.1)
            self.log(f"Connected: {port} @ {baud}", "amber")
            while self._running:
                line = self._serial.readline()
                if line:
                    self.log(line.decode(errors="replace").rstrip())
        except ImportError:
            self.log("pyserial not installed — pip install pyserial", "red")
        except Exception as e:
            self.log(f"Error: {e}", "red")
        finally:
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass


class DeviceInfoView(ToolView):
    def __init__(self):
        super().__init__("Device Info")
        self.btn_start.hide()
        self.btn_stop.hide()
        GLib.idle_add(self._populate)

    def _populate(self):
        from bruce.core.iface import get_system_info, detect_cc1101, detect_pn532, detect_nrf24, detect_si4713
        info = get_system_info()
        self.output.append("◈ SYSTEM", "amber")
        self.output.append(f"  CPU:    {info.get('cpu', '?')}")
        self.output.append(f"  RAM:    {info.get('ram', '?')}")
        self.output.append(f"  Kernel: {info.get('kernel', '?')}")
        self.output.append(f"  Root:   {'yes' if info.get('root') else 'NO — some tools need sudo'}")
        self.output.append("\n◈ INTERFACES", "amber")
        for iface in info.get("wifi", []):
            self.output.append(f"  WiFi:   {iface}", "orange")
        for iface in info.get("bt", []):
            self.output.append(f"  BT:     {iface}", "orange")
        self.output.append("\n◈ HARDWARE MODULES", "amber")
        modules = [
            ("CC1101 (SubGHz)", detect_cc1101()),
            ("PN532 (RFID)",    detect_pn532()),
            ("NRF24L01",        detect_nrf24()),
            ("Si4713 (FM TX)",  detect_si4713()),
        ]
        for name, present in modules:
            tag = "orange" if present else "dim"
            sym = "✓" if present else "○"
            self.output.append(f"  {sym} {name}", tag)

    def run_tool(self):
        pass


class ScriptsView(ToolView):
    def __init__(self):
        self._scripts_dir = Path.home() / "bruce-laptop" / "scripts"
        self._file_combo = None
        self._files: list[Path] = []
        self._refresh_files()
        super().__init__("Script Runner")

    def _refresh_files(self):
        self._files = sorted(self._scripts_dir.glob("*.sh")) + sorted(self._scripts_dir.glob("*.py"))

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        names = [f.name for f in self._files] or ["(no scripts)"]
        self._file_combo = Gtk.DropDown.new_from_strings(names)
        lbl = Gtk.Label(label="Script")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._file_combo)
        refresh_btn = Gtk.Button(label="⟳")
        refresh_btn.add_css_class("btn-action")
        refresh_btn.connect("clicked", self._on_refresh)
        bar.append(refresh_btn)
        return bar

    def _on_refresh(self, _btn):
        self._refresh_files()
        self.log(f"Found {len(self._files)} script(s).", "amber")

    def run_tool(self):
        if not self._files:
            self.log(f"No scripts in {self._scripts_dir}", "dim")
            self.log(f"Drop .sh or .py files there and click ⟳", "dim")
            return
        idx = self._file_combo.get_selected()
        if idx >= len(self._files):
            return
        script = self._files[idx]
        self.log(f"Running: {script.name}", "amber")
        if script.suffix == ".py":
            self.stream_cmd(["python3", str(script)], use_sudo=False)
        else:
            self.stream_cmd(["bash", str(script)], use_sudo=False)


class FilesView(ToolView):
    def __init__(self):
        super().__init__("Loot Files")
        self.btn_start.hide()
        self.btn_stop.hide()
        GLib.idle_add(self._list_files)

    def _list_files(self):
        loot = STATE.loot_path
        self.output.append(f"◈ Loot directory: {loot}", "amber")
        total = 0
        for sub in sorted(loot.iterdir()):
            files = list(sub.iterdir()) if sub.is_dir() else []
            self.output.append(f"\n  [{sub.name}]  {len(files)} file(s)", "orange")
            for f in sorted(files):
                size = f.stat().st_size
                self.output.append(f"    {f.name}  ({size} bytes)", "dim")
                total += 1
        self.output.append(f"\n  Total: {total} file(s)", "amber")

    def run_tool(self):
        pass


class WebUIView(ToolView):
    def __init__(self):
        self._port_entry = Gtk.Entry()
        self._port_entry.set_text("8888")
        self._port_entry.set_max_width_chars(6)
        self._port_entry.add_css_class("field-input")
        super().__init__("WebUI")

    def build_controls(self) -> Gtk.Widget:
        bar = Gtk.Box(spacing=10)
        lbl = Gtk.Label(label="Port")
        lbl.add_css_class("field-label")
        bar.append(lbl)
        bar.append(self._port_entry)
        return bar

    def run_tool(self):
        port = self._port_entry.get_text().strip() or "8888"
        self.log(f"Starting Bruce WebUI on http://localhost:{port}", "amber")
        self.log("Default credentials: admin / bruce", "dim")

        try:
            from flask import Flask, jsonify, render_template_string
            app = Flask("bruce")

            INDEX = """
<!DOCTYPE html><html><head>
<title>Bruce WebUI</title>
<style>
body{background:#080604;color:#ff8800;font-family:monospace;padding:20px;}
h1{color:#ff6600;} a{color:#ffaa00;}
</style></head><body>
<h1>Bruce Laptop</h1>
<p>Loot directory: {{ loot }}</p>
<ul>
{% for f in files %}<li><a href="/loot/{{ f }}">{{ f }}</a></li>{% endfor %}
</ul></body></html>"""

            @app.route("/")
            def index():
                files = [str(f.relative_to(STATE.loot_path))
                         for f in STATE.loot_path.rglob("*") if f.is_file()]
                return render_template_string(INDEX, loot=STATE.loot_path, files=files)

            @app.route("/api/status")
            def status():
                return jsonify({"status": "online", "mode": STATE.mode})

            self.log(f"WebUI running at http://localhost:{port}", "amber")
            subprocess.Popen(["xdg-open", f"http://localhost:{port}"])
            app.run(host="0.0.0.0", port=int(port), debug=False, use_reloader=False)
        except ImportError:
            self.log("flask not installed — pip install flask", "red")
        except Exception as e:
            self.log(f"Error: {e}", "red")
