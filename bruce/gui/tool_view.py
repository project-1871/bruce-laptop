import subprocess
import threading
import shlex
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Pango


class TerminalOutput(Gtk.ScrolledWindow):
    def __init__(self):
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.tv = Gtk.TextView()
        self.tv.set_editable(False)
        self.tv.set_cursor_visible(False)
        self.tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.tv.add_css_class("terminal")
        self.set_child(self.tv)

        buf = self.tv.get_buffer()
        self.tag_orange = buf.create_tag("orange", foreground="#ff6600")
        self.tag_amber  = buf.create_tag("amber",  foreground="#ffaa00")
        self.tag_red    = buf.create_tag("red",    foreground="#ff4444")
        self.tag_dim    = buf.create_tag("dim",    foreground="#553300")
        self.tag_bold   = buf.create_tag("bold",   weight=Pango.Weight.BOLD)
        # aliases used generically
        self.tag_cyan   = buf.create_tag("cyan",   foreground="#ffaa00")
        self.tag_green  = buf.create_tag("green",  foreground="#ff6600")
        self.tag_yellow = buf.create_tag("yellow", foreground="#ffcc44")

    def append(self, text: str, tag_name: str | None = None):
        buf = self.tv.get_buffer()
        end = buf.get_end_iter()
        mark = buf.create_mark(None, end, False)
        tag = getattr(self, f"tag_{tag_name}", None) if tag_name else None
        if tag:
            buf.insert_with_tags(end, text + "\n", tag)
        else:
            buf.insert(end, text + "\n")
        self.tv.scroll_mark_onscreen(mark)

    def clear(self):
        buf = self.tv.get_buffer()
        buf.delete(buf.get_start_iter(), buf.get_end_iter())

    def smart_append(self, line: str):
        s = line.strip()
        if not s:
            return
        if any(k in s for k in ("error", "Error", "ERROR", "failed", "Failed")):
            self.append(line, "red")
        elif any(k in s for k in ("warn", "WARN", "WARNING")):
            self.append(line, "yellow")
        elif any(k in s for k in ("◈", "CAPTURED", "DETECTED", "handshake")):
            self.append(line, "amber")
        elif s.startswith(("#", "$")):
            self.append(line, "dim")
        else:
            self.append(line)


class ToolView(Gtk.Box):
    def __init__(self, title: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("tool-view")
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._running = False

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.add_css_class("tool-view-header")
        self.btn_back = Gtk.Button(label="← Back")
        self.btn_back.add_css_class("btn-back")
        header.append(self.btn_back)
        title_lbl = Gtk.Label(label=f"▌ {title}")
        title_lbl.add_css_class("tool-view-title")
        title_lbl.set_hexpand(True)
        title_lbl.set_xalign(0.0)
        header.append(title_lbl)
        self.append(header)

        controls = self.build_controls()
        if controls:
            controls.add_css_class("controls-bar")
            self.append(controls)

        self.output = TerminalOutput()
        self.append(self.output)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bottom.add_css_class("controls-bar")
        self.btn_start = Gtk.Button(label="▶ Start")
        self.btn_start.add_css_class("btn-start")
        self.btn_stop = Gtk.Button(label="■ Stop")
        self.btn_stop.add_css_class("btn-stop")
        self.btn_stop.set_sensitive(False)
        self.btn_start.connect("clicked", self._on_start_clicked)
        self.btn_stop.connect("clicked", self._on_stop_clicked)
        bottom.append(self.btn_start)
        bottom.append(self.btn_stop)
        self.build_bottom_controls(bottom)
        self.append(bottom)

    def build_controls(self) -> Gtk.Widget | None:
        return None

    def build_bottom_controls(self, bar: Gtk.Box):
        pass

    def log(self, text: str, tag: str | None = None):
        GLib.idle_add(self.output.append, text, tag)

    def log_auto(self, text: str):
        GLib.idle_add(self.output.smart_append, text)

    def _on_start_clicked(self, _btn):
        self.btn_start.set_sensitive(False)
        self.btn_stop.set_sensitive(True)
        self._running = True
        self.output.clear()
        self._thread = threading.Thread(target=self._run_wrapper, daemon=True)
        self._thread.start()

    def _on_stop_clicked(self, _btn):
        self._running = False
        self.kill_proc()
        GLib.idle_add(self._reset_buttons)

    def _run_wrapper(self):
        try:
            self.run_tool()
        except Exception as e:
            GLib.idle_add(self.output.append, f"Error: {e}", "red")
        finally:
            GLib.idle_add(self._reset_buttons)

    def _reset_buttons(self):
        self._running = False
        self.btn_start.set_sensitive(True)
        self.btn_stop.set_sensitive(False)

    def run_tool(self):
        self.log("No implementation.", "dim")

    def stream_cmd(self, cmd: list[str] | str, use_sudo: bool = True):
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        if use_sudo and cmd[0] != "sudo":
            cmd = ["sudo"] + cmd
        self.log(f"$ {' '.join(cmd)}", "dim")
        self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in self._proc.stdout:
            if not self._running:
                break
            self.log_auto(line.decode(errors="replace").rstrip())
        self._proc.wait()

    def run_cmd(self, cmd: list[str] | str, use_sudo: bool = True) -> tuple[int, str]:
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        if use_sudo and cmd[0] != "sudo":
            cmd = ["sudo"] + cmd
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout + r.stderr

    def kill_proc(self):
        if self._proc:
            try:
                self._proc.kill()
                self._proc.wait()
            except Exception:
                pass


class HardwareStubView(ToolView):
    def __init__(self, title: str, module: str):
        self._module = module
        super().__init__(title)
        self.btn_start.set_sensitive(False)
        self.btn_stop.hide()
        GLib.idle_add(self._show_stub)

    def _show_stub(self):
        self.output.append("◈ HARDWARE REQUIRED", "amber")
        self.output.append("", None)
        self.output.append(f"This tool requires: {self._module}", None)
        self.output.append("", None)
        self.output.append("Connect the module and restart Bruce.", "dim")

    def run_tool(self):
        pass
