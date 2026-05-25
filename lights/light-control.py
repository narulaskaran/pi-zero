#!/usr/bin/env python3
"""
Zengge LED light control via TCP port 5577.
Protocol: ON/OFF (8 bytes), RGB (7 bytes).

Usage:
  light-control.py <light> <command> [args...]

Configuration:
  Copy lights.example.yaml to lights.yaml and set your device IPs.
  lights.yaml is gitignored — never commit real addresses.
"""

import socket
import time
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "lights.yaml")
EXAMPLE_FILE = os.path.join(SCRIPT_DIR, "lights.example.yaml")

COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "white": (255, 255, 255),
    "warm": (255, 200, 100),
    "cool": (200, 220, 255),
    "pink": (255, 50, 150),
    "purple": (128, 0, 255),
    "orange": (255, 80, 0),
    "yellow": (255, 200, 0),
    "cyan": (0, 255, 200),
    "off": (0, 0, 0),
}


def load_lights():
    """Load light registry from lights.yaml. Lightweight YAML parser — no PyYAML dependency."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file not found: {CONFIG_FILE}")
        print(f"Copy {EXAMPLE_FILE} to {CONFIG_FILE} and set your device IPs.")
        sys.exit(1)

    lights = {}
    current_light = None
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("lights:"):
                continue
            if line.endswith(":") and not line.startswith(" "):
                current_light = line[:-1].strip()
                lights[current_light] = {}
            elif current_light and ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "port":
                    val = int(val)
                lights[current_light][key] = val

    return lights


def send_cmd(ip, port, cmd_bytes):
    """Send raw bytes to light, return response if any."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((ip, port))
    s.send(cmd_bytes)
    time.sleep(0.2)
    try:
        resp = s.recv(1024)
        return resp
    except socket.timeout:
        return None
    finally:
        s.close()


def power_on(ip, port):
    send_cmd(ip, port, bytes([0x71, 0x23, 0x0F, 0xA3, 0x00, 0x00, 0x00, 0x00]))
    return "on"


def power_off(ip, port):
    send_cmd(ip, port, bytes([0x71, 0x24, 0x0F, 0xA4, 0x00, 0x00, 0x00, 0x00]))
    return "off"


def set_rgb(ip, port, r, g, b):
    send_cmd(ip, port, bytes([0x31, r, g, b, 0x00, 0xF0, 0x0F]))
    return f"rgb({r},{g},{b})"


def set_warm(ip, port, level):
    send_cmd(ip, port, bytes([0x31, 0x00, 0x00, 0x00, level, 0x0F, 0x0F]))
    return f"warm({level})"


def main():
    if len(sys.argv) < 3:
        print("Usage: light-control.py <light> <command> [args...]")
        LIGHTS = load_lights()
        print(f"Lights: {', '.join(LIGHTS.keys())}")
        sys.exit(1)

    light_name = sys.argv[1].lower()
    command = sys.argv[2].lower()

    LIGHTS = load_lights()

    if light_name not in LIGHTS:
        print(f"Unknown light: {light_name}")
        print(f"Known: {', '.join(LIGHTS.keys())}")
        sys.exit(1)

    light = LIGHTS[light_name]
    ip = light["ip"]
    port = light["port"]

    try:
        if command == "on":
            result = power_on(ip, port)
        elif command == "off":
            result = power_off(ip, port)
        elif command == "color" and len(sys.argv) >= 6:
            r, g, b = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
            result = set_rgb(ip, port, r, g, b)
        elif command == "warm" and len(sys.argv) >= 4:
            level = int(sys.argv[3])
            result = set_warm(ip, port, level)
        elif command in COLORS:
            r, g, b = COLORS[command]
            if command == "off":
                result = power_off(ip, port)
            else:
                result = set_rgb(ip, port, r, g, b)
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

        print(f"OK: {light_name} -> {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
