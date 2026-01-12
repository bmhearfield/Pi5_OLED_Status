# Raspberry Pi 5 OLED Stats Display

A customizable OLED stats display for Raspberry Pi with dynamic icons, configurable thresholds, and shutdown detection.

## Features

- 📊 **System Stats**: Load average, CPU temperature, memory usage, disk usage
- 🔄 **Rotating Display**: Cycles through hostname, LAN IP, and WiFi IP
- 🔥 **Dynamic Icons**: Icons change based on system state (normal → warning)
- ⚙️ **Fully Configurable**: JSON config for fonts, thresholds, and icons
- ⚡ **Graceful Shutdown**: Displays "OFFLINE" when Pi shuts down
- 🎯 **Zero Dependencies Mode**: Works without icon fonts (graceful fallback)

## Display Layout

**Normal Operation:**

![Status Screen](/Images/Status_Screen.jpg)


```
[🖥️] hostname        ← Rotates: hostname → LAN IP → WiFi IP
[⚡] 0.15  [🌡️] 45C   ← Load (⚡→🔥 if high) + Temp (🌡️→🔥 if hot)
[📊] 0.4/3.7GB 11%   ← Memory (📊→⚠️ if high)
[💽] 4/29GB 15%      ← Disk (💽→⚠️ if full)
```

**Shutdown/Offline:**
```
hostname
[⏻] OFFLINE
```

## Folder Structure

```
Pi5_OLED_Status/
├── config.json          # Configuration file
├── README.md            # This file
├── Scripts/
│   └── status.py         # Main display script
└── Fonts/
    ├── PixelOperator.ttf       # Text font
    ├── PixelOperator-Bold.ttf  # Bold variant
    └── la-solid-900.ttf        # Line Awesome icons
```

## Hardware Requirements

- Raspberry Pi (tested on Pi 5, compatible with Pi 4, Pi Zero 2W)
- 0.96" I2C OLED Display (SSD1306, 128x64)
- 4x Female-to-Female jumper wires

## Wiring

| OLED Pin | Pi Pin | Pi GPIO |
|----------|--------|---------|
| GND      | Pin 9  | Ground  |
| VCC      | Pin 1  | 3.3V    |
| SCL      | Pin 5  | GPIO 3  |
| SDA      | Pin 3  | GPIO 2  |

> ⚠️ **Warning**: Check your display's pinout - some have GND and VCC swapped!

---

## Quick Start

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/piwakawaka-ca/Pi5_OLED_Status.git
cd Pi5_OLED_Status
```

### 2. Install Dependencies

```bash
# System packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-pil i2c-tools

# Enable I2C
sudo raspi-config  # Interface Options → I2C → Yes

# Create virtual environment
python3 -m venv ~/stats_env --system-site-packages
source ~/stats_env/bin/activate

# Install Python packages
pip3 install adafruit-circuitpython-ssd1306
```

### 3. Test

```bash
source ~/stats_env/bin/activate
python3 Scripts/status.py
```

Press `Ctrl+C` to stop - you should see the "OFFLINE" screen.

---

## Configuration

Edit `config.json` to customize everything:

```json
{
    "display": {
        "width": 128,
        "height": 64,
        "i2c_address": "0x3C",
        "rotation": 0
    },
    "timing": {
        "refresh_interval": 1.0,
        "rotation_interval": 3
    },
    "fonts": {
        "text_font": "PixelOperator.ttf",
        "text_size": 16,
        "text_size_large": 24,
        "icon_font": "la-solid-900.ttf",
        "icon_size": 14
    },
    "thresholds": {
        "load_warn": 2.0,
        "temp_warn": 70,
        "mem_warn": 80,
        "disk_warn": 80
    },
    "icons": {
        "hostname": "\uf108",
        "wifi": "\uf1eb",
        "lan": "\uf6ff",
        "offline": "\uf011",
        "load_normal": "\uf0e7",
        "load_warn": "\uf06d",
        "temp_normal": "\uf2c9",
        "temp_warn": "\uf06d",
        "mem_normal": "\uf0ae",
        "mem_warn": "\uf071",
        "disk_normal": "\uf0a0",
        "disk_warn": "\uf071"
    }
}
```

### Configuration Options

| Section | Setting | Description | Default |
|---------|---------|-------------|---------|
| **display** | `width` | Display width in pixels | 128 |
| | `height` | Display height in pixels | 64 |
| | `i2c_address` | I2C address (hex string) | "0x3C" |
| | `rotation` | Screen rotation (0 or 2) | 0 |
| **timing** | `refresh_interval` | Screen refresh rate (seconds) | 1.0 |
| | `rotation_interval` | Network info rotation (seconds) | 3 |
| **fonts** | `text_font` | Main text font filename | "PixelOperator.ttf" |
| | `text_size` | Main text size | 16 |
| | `text_size_large` | Large text size (OFFLINE) | 24 |
| | `icon_font` | Icon font filename | "la-solid-900.ttf" |
| | `icon_size` | Icon size in pixels | 14 |
| **thresholds** | `load_warn` | Load average warning threshold | 2.0 |
| | `temp_warn` | Temperature warning (°C) | 70 |
| | `mem_warn` | Memory usage warning (%) | 80 |
| | `disk_warn` | Disk usage warning (%) | 80 |

### Dynamic Icons

Icons automatically change when values exceed thresholds:

| Metric | Normal | Warning | Trigger |
|--------|--------|---------|---------|
| **Load** | ⚡ bolt | 🔥 fire | > load_warn |
| **Temperature** | 🌡️ thermometer | 🔥 fire | > temp_warn |
| **Memory** | 📊 tasks | ⚠️ warning | > mem_warn |
| **Disk** | 💽 hdd | ⚠️ warning | > disk_warn |

### Available Icons (Line Awesome / Font Awesome)

| Icon | Name | Unicode | Use For |
|------|------|---------|---------|
| 🖥️ | desktop | `\uf108` | Hostname |
| 📶 | wifi | `\uf1eb` | WiFi IP |
| 🔌 | network-wired | `\uf6ff` | LAN IP |
| ⚡ | bolt | `\uf0e7` | Normal load |
| 🔥 | fire | `\uf06d` | High load/temp |
| 🌡️ | thermometer-half | `\uf2c9` | Normal temp |
| 📊 | tasks | `\uf0ae` | Normal memory |
| 💽 | hdd-o | `\uf0a0` | Normal disk |
| ⚠️ | exclamation-triangle | `\uf071` | Warning state |
| ⏻ | power-off | `\uf011` | Offline |

Find more icons: [Line Awesome Cheatsheet](https://icons8.com/line-awesome)

---

## Running as a Service

### Create Service File

```bash
sudo nano /etc/systemd/system/pi5-oled-status.service
```

```ini
[Unit]
Description=Pi 5 OLED Status Display
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
Environment=PATH=/home/YOUR_USERNAME/stats_env/bin:/usr/bin:/bin
WorkingDirectory=/home/YOUR_USERNAME/Pi5_OLED_Status/Scripts
ExecStart=/home/YOUR_USERNAME/stats_env/bin/python3 /home/YOUR_USERNAME/Pi5_OLED_Status/Scripts/status.py
Restart=on-failure
RestartSec=5
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
```

Replace `YOUR_USERNAME` with your actual username.

### Enable Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable pi5-oled-status.service
sudo systemctl start pi5-oled-status.service
```

### Verify

```bash
sudo systemctl status pi5-oled-status.service
```

---

## Testing Dynamic Icons

Use `stress-ng` to trigger the warning icons:

```bash
# Install stress-ng
sudo apt-get install -y stress-ng

# Spike CPU load (triggers fire icon when load > 2.0)
stress-ng --cpu 4 --timeout 30s

# Max out all cores for 15 seconds
stress-ng --cpu 0 --timeout 15s

# Test CPU + Memory together
stress-ng --cpu 2 --vm 1 --vm-bytes 1G --timeout 30s
```

Watch the display - you should see:
- ⚡ → 🔥 when load exceeds threshold (default: 2.0)
- 🌡️ → 🔥 when temperature exceeds threshold (default: 70°C)

**Tip:** To test without stressing your Pi, temporarily lower thresholds in `config.json`:
```json
"thresholds": {
    "load_warn": 0.5,
    "temp_warn": 45
}
```
Then restart the service: `sudo systemctl restart pi5-oled-status`

---

## Useful Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl status pi5-oled-status` | Check service status |
| `sudo systemctl restart pi5-oled-status` | Restart after config changes |
| `sudo systemctl stop pi5-oled-status` | Stop (shows OFFLINE) |
| `journalctl -u pi5-oled-status -f` | View live logs |
| `sudo i2cdetect -y 1` | Check display connection |

---

## Troubleshooting

### Display not detected
```bash
sudo i2cdetect -y 1
```
- Should show `3c` (or `3d`)
- Check wiring and I2C enabled in raspi-config

### GPIO busy error
```bash
pkill -9 -f status.py
```

### Icons not showing
- Script works without icons (graceful fallback)
- Check `la-solid-900.ttf` exists in `Fonts/`
- Verify `icon_font` path in config.json

### Service won't start
```bash
journalctl -u pi5-oled-status -n 50
```
Common fixes:
- Correct username in service file
- Font files exist
- Virtual environment path correct

---

## Disabling Icons

To run without icons, either:

1. **Delete the icon font file** - Script auto-detects and falls back
2. **Set invalid path** in config.json:
   ```json
   "icon_font": "disabled"
   ```

---

## Credits

- Original inspiration: [Michael Klements' OLED Stats](https://github.com/mklements/OLED_Stats) / [The DIY Life](https://the-diy-life.com/)
- Icons: [Line Awesome](https://icons8.com/line-awesome) by Icons8
- Font: [PixelOperator](https://www.dafont.com/pixel-operator.font)

## License

MIT License - Feel free to modify and share!