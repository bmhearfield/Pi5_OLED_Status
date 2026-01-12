# OLED Stats Display for Raspberry Pi
# Displays system stats with dynamic icons and shutdown detection
# Supports configuration via config.json

import time
import board
import busio
import gpiozero
import os
import signal
import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import subprocess

# Get the script directory for relative paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent  # Go up from Scripts/ to project root

def load_config():
    """Load configuration from config.json"""
    config_path = PROJECT_DIR / "config.json"
    
    # Default configuration
    default_config = {
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
    
    try:
        with open(config_path, 'r') as f:
            user_config = json.load(f)
            # Merge user config with defaults
            for key in default_config:
                if key in user_config:
                    if isinstance(default_config[key], dict):
                        default_config[key].update(user_config[key])
                    else:
                        default_config[key] = user_config[key]
            return default_config
    except FileNotFoundError:
        print(f"Config file not found at {config_path}, using defaults")
        return default_config
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}, using defaults")
        return default_config

# Load configuration
config = load_config()

# Display Parameters
WIDTH = config["display"]["width"]
HEIGHT = config["display"]["height"]
I2C_ADDRESS = int(config["display"]["i2c_address"], 16)
ROTATION = config["display"]["rotation"]

# Timing
LOOPTIME = config["timing"]["refresh_interval"]
ROTATION_INTERVAL = config["timing"]["rotation_interval"]

# Font paths
FONTS_DIR = PROJECT_DIR / "Fonts"
TEXT_FONT_PATH = FONTS_DIR / config["fonts"]["text_font"]
ICON_FONT_PATH = FONTS_DIR / config["fonts"]["icon_font"]

# Thresholds
THRESHOLDS = config["thresholds"]

# Icons
ICONS = config["icons"]

# Icon width for text offset (will be set after font loads)
ICON_WIDTH = 0

# Use gpiozero to control the reset pin
oled_reset_pin = gpiozero.OutputDevice(4, active_high=False)

# Use I2C for communication
i2c = board.I2C()

# Manually reset the display
oled_reset_pin.on()
time.sleep(0.1)
oled_reset_pin.off()
time.sleep(0.1)
oled_reset_pin.on()

# Create the OLED display object
oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=I2C_ADDRESS)

# Set display rotation
if ROTATION == 2:
    try:
        oled.rotate(2)
    except AttributeError:
        oled.rotation = 2

# Create a blank image for drawing
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)

# Load fonts
try:
    font = ImageFont.truetype(str(TEXT_FONT_PATH), config["fonts"]["text_size"])
    font_large = ImageFont.truetype(str(TEXT_FONT_PATH), config["fonts"]["text_size_large"])
except OSError as e:
    print(f"Error loading text font: {e}")
    print(f"Tried path: {TEXT_FONT_PATH}")
    sys.exit(1)

# Load icon font (optional - will work without it)
ICONS_AVAILABLE = False
icon_font = None
icon_font_large = None
try:
    icon_font = ImageFont.truetype(str(ICON_FONT_PATH), config["fonts"]["icon_size"])
    icon_font_large = ImageFont.truetype(str(ICON_FONT_PATH), config["fonts"]["text_size_large"])
    ICONS_AVAILABLE = True
    # Calculate icon width for consistent spacing
    ICON_WIDTH = config["fonts"]["icon_size"] + 2
    ICON_WIDTH_LARGE = config["fonts"]["text_size_large"] + 2
except OSError:
    print(f"Icon font not found at {ICON_FONT_PATH}, running without icons")
    ICONS_AVAILABLE = False

# Get hostname once at startup for use in signal handler
try:
    HOSTNAME = subprocess.check_output("hostname", shell=True).decode('utf-8').strip()
except:
    HOSTNAME = "Pi"

def get_network_info():
    """Get hostname and physical network interfaces with IPs"""
    info_list = []
    
    # Add hostname
    info_list.append(("hostname", HOSTNAME))
    
    # Get physical network interfaces and their IPs
    try:
        cmd = "ip -4 -o addr show | awk '!/^[0-9]+: lo/ {print $2, $4}' | cut -d/ -f1"
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        
        for line in output.split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    interface = parts[0]
                    ip = parts[1]
                    
                    # Only include physical interfaces (skip docker, veth, br, tailscale, etc.)
                    skip_prefixes = ('docker', 'br-', 'veth', 'tailscale', 'tun', 'tap')
                    if any(interface.startswith(p) for p in skip_prefixes):
                        continue
                    
                    if interface.startswith('eth') or interface.startswith('en'):
                        info_list.append(("lan", ip))
                    elif interface.startswith('wlan') or interface.startswith('wl'):
                        info_list.append(("wifi", ip))
    except:
        pass
    
    return info_list

def draw_icon(x, y, icon_key):
    """Draw an icon at the specified position, return width used"""
    if ICONS_AVAILABLE and icon_key in ICONS:
        draw.text((x, y), ICONS[icon_key], font=icon_font, fill=255)
        return ICON_WIDTH
    return 0

def get_icon_for_value(base_name, value, threshold):
    """Get the appropriate icon based on value vs threshold"""
    if value >= threshold:
        return f"{base_name}_warn"
    return f"{base_name}_normal"

def show_offline_screen():
    """Display an offline message when shutting down"""
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    
    # Line 1: Hostname
    draw.text((10, 8), HOSTNAME, font=font, fill=255)
    
    # Line 2: Power icon + OFFLINE (both large, same line)
    if ICONS_AVAILABLE:
        draw.text((10, 32), ICONS["offline"], font=icon_font_large, fill=255)
        draw.text((10 + ICON_WIDTH_LARGE, 32), "OFFLINE", font=font_large, fill=255)
    else:
        draw.text((10, 32), "OFFLINE", font=font_large, fill=255)
    
    oled.image(image)
    oled.show()

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    try:
        show_offline_screen()
    except:
        pass
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Clear the display on startup
oled.fill(0)
oled.show()

# Rotation tracking
rotation_index = 0
loop_counter = 0

while True:
    try:
        # Draw a black filled box to clear the image
        draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)

        # Get network info (hostname + physical IPs only)
        network_info = get_network_info()
        
        # Rotate through network info every ROTATION_INTERVAL seconds
        if loop_counter >= ROTATION_INTERVAL:
            rotation_index = (rotation_index + 1) % len(network_info)
            loop_counter = 0
        
        # Get current network info item
        if network_info:
            info_type, info_value = network_info[rotation_index % len(network_info)]
        else:
            info_type, info_value = "hostname", "No network"

        # Get load average (1-minute)
        load_raw = subprocess.check_output("cat /proc/loadavg | awk '{print $1}'", shell=True).decode('utf-8').strip()
        try:
            load_value = float(load_raw)
        except:
            load_value = 0.0

        # Get temperature
        temp_raw = subprocess.check_output("cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -1", shell=True).decode('utf-8').strip()
        try:
            temp_value = float(temp_raw) / 1000
        except:
            temp_value = 0.0

        # Get memory usage
        mem_output = subprocess.check_output("free | awk 'NR==2{printf \"%.1f %.1f %.0f\", $3/1024/1024, $2/1024/1024, ($3/$2)*100}'", shell=True).decode('utf-8').strip()
        mem_parts = mem_output.split()
        try:
            mem_used_gb = mem_parts[0]
            mem_total_gb = mem_parts[1]
            mem_percent = float(mem_parts[2])
        except:
            mem_used_gb = "0"
            mem_total_gb = "0"
            mem_percent = 0

        # Get disk usage
        disk_output = subprocess.check_output("df -h / | awk 'NR==2{print $3, $2, $5}'", shell=True).decode('utf-8').strip()
        disk_parts = disk_output.split()
        try:
            disk_used = disk_parts[0].rstrip('G')
            disk_total = disk_parts[1].rstrip('G')
            disk_percent = float(disk_parts[2].rstrip('%'))
        except:
            disk_used = "0"
            disk_total = "0"
            disk_percent = 0

        # Line positions
        line1_y = 0
        line2_y = 16
        line3_y = 32
        line4_y = 48

        # === LINE 1: Network info (rotating) ===
        x = 0
        if ICONS_AVAILABLE:
            x += draw_icon(x, line1_y, info_type)
        draw.text((x, line1_y), info_value, font=font, fill=255)

        # === LINE 2: Load + Temperature ===
        x = 0
        load_icon = get_icon_for_value("load", load_value, THRESHOLDS["load_warn"])
        if ICONS_AVAILABLE:
            x += draw_icon(x, line2_y, load_icon)
        draw.text((x, line2_y), f"{load_value:.2f}", font=font, fill=255)
        
        # Temperature on right side of line 2
        temp_icon = get_icon_for_value("temp", temp_value, THRESHOLDS["temp_warn"])
        temp_str = f"{temp_value:.0f}C"
        if ICONS_AVAILABLE:
            # Position: right-align temp with icon
            temp_x = 75
            draw_icon(temp_x, line2_y, temp_icon)
            draw.text((temp_x + ICON_WIDTH, line2_y), temp_str, font=font, fill=255)
        else:
            draw.text((80, line2_y), temp_str, font=font, fill=255)

        # === LINE 3: Memory ===
        x = 0
        mem_icon = get_icon_for_value("mem", mem_percent, THRESHOLDS["mem_warn"])
        if ICONS_AVAILABLE:
            x += draw_icon(x, line3_y, mem_icon)
        mem_display = f"{mem_used_gb}/{mem_total_gb}GB {mem_percent:.0f}%"
        draw.text((x, line3_y), mem_display, font=font, fill=255)

        # === LINE 4: Disk ===
        x = 0
        disk_icon = get_icon_for_value("disk", disk_percent, THRESHOLDS["disk_warn"])
        if ICONS_AVAILABLE:
            x += draw_icon(x, line4_y, disk_icon)
        disk_display = f"{disk_used}/{disk_total}GB {disk_percent:.0f}%"
        draw.text((x, line4_y), disk_display, font=font, fill=255)

        # Display the image
        oled.image(image)
        oled.show()

        loop_counter += 1

    except Exception as e:
        # Silently continue on errors
        pass

    time.sleep(LOOPTIME)