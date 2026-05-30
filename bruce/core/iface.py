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


def _get_phy(iface: str) -> str:
    try:
        return Path(f"/sys/class/net/{iface}/phy80211").resolve().name
    except Exception:
        return "phy0"


def _get_chipset(iface: str) -> str:
    try:
        return Path(f"/sys/class/net/{iface}/device/driver").resolve().name
    except Exception:
        return "unknown"


def get_adapter_info(iface: str) -> dict:
    info = {
        "iface": iface,
        "phy": _get_phy(iface),
        "chipset": _get_chipset(iface),
        "bands": [],
        "monitor": False,
        "injection": False,
        "tx_power_dbm": None,
        "mode": "unknown",
    }
    try:
        r = subprocess.run(["iw", "phy", info["phy"], "info"],
                           capture_output=True, text=True, timeout=5)
        out = r.stdout
        if "monitor" in out:
            info["monitor"] = True
        if any(f in out for f in ("2412", "2437", "2462")):
            info["bands"].append("2.4GHz")
        if any(f in out for f in ("5180", "5240", "5745")):
            info["bands"].append("5GHz")
        if "\tAP\n" in out or " AP\n" in out:
            info["injection"] = True
    except Exception:
        pass
    try:
        r = subprocess.run(["iw", "dev", iface, "info"],
                           capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            ls = line.strip()
            if ls.startswith("type "):
                info["mode"] = ls.split()[1]
            elif "txpower" in ls:
                parts = ls.split()
                try:
                    info["tx_power_dbm"] = float(parts[1])
                except Exception:
                    pass
    except Exception:
        pass
    return info


def set_tx_power(iface: str, dbm: float) -> tuple[bool, str]:
    mdbm = int(dbm * 100)
    try:
        r = _sudo_run(["iw", "dev", iface, "set", "txpower", "fixed", str(mdbm)],
                      capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return True, f"{iface} TX power → {dbm:.1f} dBm"
        return False, r.stderr.strip() or f"set txpower failed (rc={r.returncode})"
    except Exception as e:
        return False, str(e)


def set_tx_power_auto(iface: str) -> tuple[bool, str]:
    try:
        r = _sudo_run(["iw", "dev", iface, "set", "txpower", "auto"],
                      capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return True, f"{iface} TX power → auto (driver max)"
        return False, r.stderr.strip() or f"set txpower auto failed (rc={r.returncode})"
    except Exception as e:
        return False, str(e)


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
