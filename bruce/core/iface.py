import subprocess
import os
from pathlib import Path


def get_wifi_interfaces() -> list[str]:
    ifaces = []
    for p in Path("/sys/class/net").iterdir():
        if (p / "wireless").exists() or (p / "phy80211").exists():
            ifaces.append(p.name)
    return sorted(ifaces)


def get_bt_interfaces() -> list[str]:
    bt = Path("/sys/class/bluetooth")
    if not bt.exists():
        return []
    return sorted(p.name for p in bt.iterdir())


def is_root() -> bool:
    return os.geteuid() == 0


def _sudo_run(cmd: list[str], **kwargs):
    from bruce.core.state import STATE
    pw = STATE.sudo_password
    if pw:
        return subprocess.run(["sudo", "-S"] + cmd, input=pw + "\n", text=True, **kwargs)
    return subprocess.run(["sudo"] + cmd, **kwargs)


def set_monitor_mode(iface: str) -> tuple[bool, str]:
    try:
        _sudo_run(["ip", "link", "set", iface, "down"], timeout=5)
        _sudo_run(["iw", "dev", iface, "set", "type", "monitor"], timeout=5)
        _sudo_run(["ip", "link", "set", iface, "up"], timeout=5)
        return True, f"{iface} → monitor"
    except Exception as e:
        return False, str(e)


def set_managed_mode(iface: str) -> tuple[bool, str]:
    try:
        _sudo_run(["ip", "link", "set", iface, "down"], timeout=5)
        _sudo_run(["iw", "dev", iface, "set", "type", "managed"], timeout=5)
        _sudo_run(["ip", "link", "set", iface, "up"], timeout=5)
        return True, f"{iface} → managed"
    except Exception as e:
        return False, str(e)


def check_usb_module(vid: str, pid: str) -> bool:
    try:
        out = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5).stdout
        return f"{vid}:{pid}".lower() in out.lower()
    except Exception:
        return False


def detect_cc1101() -> bool:
    return check_usb_module("1a86", "5523") or check_usb_module("0403", "6015")


def detect_pn532() -> bool:
    return check_usb_module("04cc", "2533") or check_usb_module("054c", "06c3")


def detect_nrf24() -> bool:
    return check_usb_module("1a86", "5512") or check_usb_module("0403", "6001")


def detect_si4713() -> bool:
    try:
        out = subprocess.run(["i2cdetect", "-y", "1"], capture_output=True, text=True, timeout=5).stdout
        return "63" in out
    except Exception:
        return False


def get_system_info() -> dict:
    info: dict = {}
    try:
        for line in open("/proc/cpuinfo"):
            if "model name" in line:
                info["cpu"] = line.split(":")[1].strip()
                break
    except Exception:
        info["cpu"] = "Unknown"
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal"):
                info["ram"] = f"{int(line.split()[1]) // 1024} MB"
                break
    except Exception:
        info["ram"] = "Unknown"
    try:
        info["kernel"] = subprocess.run(["uname", "-r"], capture_output=True, text=True).stdout.strip()
    except Exception:
        info["kernel"] = "Unknown"
    info["wifi"] = get_wifi_interfaces()
    info["bt"] = get_bt_interfaces()
    info["root"] = is_root()
    return info
