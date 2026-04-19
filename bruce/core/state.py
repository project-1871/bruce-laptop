import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "bruce" / "config.json"
LOOT_PATH = Path.home() / ".local" / "share" / "bruce" / "loot"

DEFAULTS = {
    "mode": None,
    "wifi_iface": "",
    "bt_iface": "hci0",
}


class State:
    def __init__(self):
        self.config = dict(DEFAULTS)
        self._load()
        for sub in ("eapol", "wardriving", "ble", "pcap", "scripts", "qr"):
            (LOOT_PATH / sub).mkdir(parents=True, exist_ok=True)

    def _load(self):
        if CONFIG_PATH.exists():
            try:
                self.config.update(json.loads(CONFIG_PATH.read_text()))
            except Exception:
                pass

    def save(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self.config, indent=2))

    @property
    def mode(self) -> str | None:
        return self.config.get("mode")

    @mode.setter
    def mode(self, v: str):
        self.config["mode"] = v
        self.save()

    @property
    def wifi_iface(self) -> str:
        return self.config.get("wifi_iface", "")

    @wifi_iface.setter
    def wifi_iface(self, v: str):
        self.config["wifi_iface"] = v
        self.save()

    @property
    def is_offensive(self) -> bool:
        return self.config.get("mode") == "OFFENSIVE"

    @property
    def loot_path(self) -> Path:
        return LOOT_PATH


STATE = State()
