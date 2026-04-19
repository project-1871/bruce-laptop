# Bruce Laptop

A GTK4 desktop security toolkit for Linux, modelled on the [Bruce ESP32 firmware](https://github.com/pr3y/Bruce) by pr3y. Brings Bruce's feature set to your laptop — orange terminal aesthetic, native Linux tools, and optional hardware module support (CC1101, PN532, NRF24L01, Si4713).

> **For authorized testing only.** Only use against networks and devices you own or have explicit written permission to test.

---

## Screenshots

```
┌─────────────────────────────────────────────────────┐
│  ▌ OFFENSIVE                          [bruce icon]  │
├──────────────┬──────────────────────────────────────┤
│ Bruce        │  ▶ 01  WiFi                          │
│              │  8 tools available                   │
│ 01  WiFi     │                                      │
│ 02  BLE      │  [Scan APs]    [Deauth]              │
│ 03  RF/SubGHz│  [Beacon Spam] [Evil Portal]         │
│ 04  RFID/NFC │  [RAW Sniffer] [Scan Hosts]          │
│ 05  IR       │  [Wardriving]  [Brucegotchi]         │
│ 06  NRF24    │                                      │
│ 07  FM Radio │                                      │
│ 08  Scripts  │                                      │
│ 09  Others   │                                      │
│ 10  Files    │                                      │
│ 11  WebUI    │                                      │
│ 12  Settings │                                      │
│ 13  About    │                                      │
└──────────────┴──────────────────────────────────────┘
```

---

## Features

### 01 — WiFi
| Tool | Description | Needs Root |
|------|-------------|------------|
| Scan APs | Passive scan via `iwlist` / `iw scan` | No |
| Deauth | Send 802.11 deauth frames via `aireplay-ng` | Yes |
| Beacon Spam | Flood SSID beacons via `mdk4` | Yes |
| Evil Portal | Rogue AP with captive portal via `hostapd` | Yes |
| RAW Sniffer / PCAP | Capture 802.11 frames to `.pcap` via `tcpdump` | Yes |
| Scan Hosts | ARP scan + port detection via `nmap` | Yes |
| Wardriving | Multi-channel AP logging (GPS optional) | No |
| Brucegotchi | Channel-hopping handshake collector | Yes |

### 02 — BLE
| Tool | Description |
|------|-------------|
| BLE Scan | Discover nearby BLE devices with RSSI |
| Tracker Scan | Detect AirTags, Tile, Samsung SmartTag by manufacturer ID |
| Phantom Flood | Flood nearby devices with fake BLE advertisements |
| BLE Beacon | Broadcast custom BLE advertisement payloads |
| BLE Predator | Aggressive device fingerprinting — enumerate all GATT services |
| Media Commands | playerctl / pactl / grim media and system commands |

### 03 — RF / SubGHz `[CC1101 required]`
Scan, replay, brute-force, jam, and spectrum-analyse SubGHz signals (300–928 MHz). Import and replay Flipper Zero `.sub` files.

### 04 — RFID / NFC `[PN532 required]`
Read, write, clone, brute-force keys, and emulate MIFARE / NFC tags.

### 05 — IR `[KY-005 / KY-022 required]`
TV-B-Gone, IR signal capture and replay. Supports NEC, RC5, Samsung32 and other protocols.

### 06 — NRF24 `[NRF24L01+PA+LNA required]`
2.4 GHz channel jam, spectrum analysis, MouseJack.

### 07 — FM Radio `[Si4713 required]`
FM broadcast on 76–108 MHz, spectrum analysis.

### 08 — Scripts
Run `.sh` or `.py` scripts from `~/bruce-laptop/scripts/`. Drop files in the folder and hit refresh.

### 09 — Others
| Tool | Description |
|------|-------------|
| QR Code Generator | Generate and display QR codes from any text/URL |
| Timer | Configurable countdown with desktop notification |
| Serial Monitor | Connect to USB serial devices (ESP32, Arduino, etc.) |
| Device Info | Show system hardware, interfaces, and module detection status |

### 10 — Files
Browse the loot directory (`~/.local/share/bruce/loot/`). View all captured data: PCAPs, EAPOL handshakes, wardriving logs, BLE data.

### 11 — WebUI
Launch a local Flask web interface (`http://localhost:8888`) to browse loot and check device status remotely.

---

## Operating Modes

| Mode | Description |
|------|-------------|
| **OFFENSIVE** | Full toolkit — all attack tools enabled |
| **MONITOR** | Passive / defensive tools only |

Mode is selected on first launch and can be changed in Settings at any time.

---

## Requirements

### System packages
```bash
sudo pacman -S iw wireless_tools aircrack-ng mdk4 nmap hostapd dnsmasq tcpdump bluez-utils playerctl libnotify grim
```

### Python packages
```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
textual
bleak
scapy
netifaces
pyserial
qrcode[pil]
Pillow
flask
flask-cors
```

### GTK4
```bash
sudo pacman -S python-gobject gtk4
```

### Optional hardware modules
| Module | Section | Notes |
|--------|---------|-------|
| CC1101 (SPI) | RF / SubGHz | Connect via SPI; 300–928 MHz |
| PN532 (USB or I²C) | RFID / NFC | MIFARE Classic, NDEF, emulation |
| NRF24L01+PA+LNA | NRF24 | SPI; remove SD card to avoid conflict |
| Si4713 (I²C) | FM Radio | Auto-detected on I²C bus 1, addr 0x63 |
| KY-005 + KY-022 | IR | GPIO; set TX/RX pins in Settings |

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/bruce-laptop
cd bruce-laptop
pip install -r requirements.txt
```

---

## Running

```bash
# Full functionality (monitor mode, raw sockets, root tools)
sudo python3 main.py

# Non-root (WiFi scan, BLE, QR, serial, scripts work fine)
python3 main.py

# TUI fallback (no GTK)
python3 main.py --tui

# Convenience launcher (auto-sudo via pkexec)
bash bruce.sh
```

Or launch from your application menu — Bruce Laptop appears in the Security category.

---

## Project Structure

```
bruce-laptop/
├── main.py                     # Entry point
├── bruce.sh                    # Launcher (pkexec sudo wrapper)
├── requirements.txt
├── assets/
│   └── bruce.svg               # App icon
├── scripts/                    # Drop your .sh / .py scripts here
│   └── demo.sh
└── bruce/
    ├── app.py                  # TUI fallback (Textual)
    ├── core/
    │   ├── state.py            # Config and runtime state
    │   ├── runner.py           # Async subprocess wrapper
    │   └── iface.py            # Interface/hardware detection
    └── gui/
        ├── app.py              # GTK Application + mode dialog
        ├── window.py           # Main window, sidebar, section routing
        ├── style.css           # Orange/amber dark terminal theme
        ├── tool_view.py        # Base ToolView + TerminalOutput widget
        ├── wifi_views.py       # WiFi tool views
        ├── ble_views.py        # BLE tool views
        └── others_views.py     # Scripts, Others, Files, WebUI views
```

---

## Loot

All captured data is saved to `~/.local/share/bruce/loot/`:

```
loot/
├── eapol/      — WPA handshake captures
├── pcap/       — Raw packet captures
├── wardriving/ — AP scan logs
├── ble/        — BLE scan results
├── scripts/    — Script output
└── qr/         — Generated QR codes
```

---

## Relationship to Bruce Firmware

This project mirrors the menu structure and feature philosophy of [pr3y/Bruce](https://github.com/pr3y/Bruce) — a security firmware for ESP32 devices (M5Stack Cardputer, CYD, T-Deck, etc.). Where Bruce runs on embedded hardware with a small TFT display, Bruce Laptop brings the same workflow to a Linux desktop using native system tools and GTK4.

Hardware-dependent features (RF, RFID, IR, NRF24, FM) show a stub until the corresponding USB/SPI module is connected and detected.

---

## License

For authorized use only. Run tools only against networks and devices you own or have explicit written permission to test.
