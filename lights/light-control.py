#!/usr/bin/env python3
"""
Zengge LED light control via TCP port 5577.
Protocol: ON/OFF (8 bytes), RGB (7 bytes).

Usage:
  light-control.py <light> <command> [args...]

Lights:
  slurp    192.168.0.102 (Zengge bulb)

Commands:
  on            Power on
  off           Power off
  red           Set color red (255,0,0)
  green         Set color green (0,255,0)
  blue          Set color blue (0,0,255)
  white         Set warm white
  color R G B   Set custom color (0-255 each)
  warm N        Set warm white level (0-255)
  cool N        Set cool white level (0-255)
"""

import socket
import time
import sys

# Light registry
LIGHTS = {
    "slurp": {"ip": "192.168.0.102", "port": 5577, "desc": "Zengge smart bulb"},
}

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
    """Set warm white. Level 0-255."""
    send_cmd(ip, port, bytes([0x31, 0x00, 0x00, 0x00, level, 0x0F, 0x0F]))
    return f"warm({level})"


def main():
    if len(sys.argv) < 3:
        print("Usage: light-control.py <light> <command> [args...]")
        print(f"Lights: {', '.join(LIGHTS.keys())}")
        sys.exit(1)

    light_name = sys.argv[1].lower()
    command = sys.argv[2].lower()

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

        print(f"OK: {light_name} → {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
