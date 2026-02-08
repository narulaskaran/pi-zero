#!/usr/bin/env python3
"""
System Monitor - Collect Raspberry Pi system information

Gathers CPU temp, RAM usage, WiFi status, and presence detection status.
"""

import os
import psutil
import subprocess
from pathlib import Path


class SystemMonitor:
    """Collects system information from Raspberry Pi."""

    def __init__(self):
        """Initialize system monitor."""
        self.presence_detector = None
        self._init_presence_detector()

    def _init_presence_detector(self):
        """Initialize presence detector if available."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "subway_train_times"))
            from presence_detector import PresenceDetector
            import yaml

            # Try to load config
            config_path = Path(__file__).parent / "config.yaml"
            if not config_path.exists():
                config_path = Path(__file__).parent.parent / "subway_train_times" / "config.yaml"

            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)

                refresh_config = config.get("refresh_rate", {})
                devices = refresh_config.get("devices", [])

                if devices:
                    self.presence_detector = PresenceDetector(mac_addresses=devices)
                    print(f"Presence detector initialized with {len(devices)} device(s)")
        except Exception as e:
            print(f"Presence detector not available: {e}")
            self.presence_detector = None

    def get_cpu_temp(self):
        """
        Get CPU temperature in Celsius.

        Returns:
            float: Temperature in °C, or None if unavailable
        """
        try:
            # Method 1: vcgencmd (Raspberry Pi specific)
            result = subprocess.run(
                ["vcgencmd", "measure_temp"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                # Output format: temp=42.8'C
                temp_str = result.stdout.strip().split("=")[1].split("'")[0]
                return float(temp_str)
        except:
            pass

        try:
            # Method 2: /sys/class/thermal (generic Linux)
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_millidegrees = int(f.read().strip())
                return temp_millidegrees / 1000.0
        except:
            pass

        return None

    def get_ram_usage(self):
        """
        Get RAM usage percentage.

        Returns:
            dict: {"percent": 45.2, "used_mb": 512, "total_mb": 1024}
        """
        try:
            mem = psutil.virtual_memory()
            return {
                "percent": mem.percent,
                "used_mb": mem.used // (1024 * 1024),
                "total_mb": mem.total // (1024 * 1024)
            }
        except:
            return {"percent": 0, "used_mb": 0, "total_mb": 0}

    def get_wifi_status(self):
        """
        Get WiFi connection status.

        Returns:
            dict: {"connected": True, "ssid": "MyNetwork", "signal": -45}
        """
        try:
            # Check if wlan0 is up
            result = subprocess.run(
                ["iwgetid", "-r"],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0 and result.stdout.strip():
                ssid = result.stdout.strip()

                # Try to get signal strength
                signal_dbm = None
                try:
                    signal_result = subprocess.run(
                        ["iwconfig", "wlan0"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    for line in signal_result.stdout.split('\n'):
                        if 'Signal level' in line:
                            # Extract signal level (e.g., "Signal level=-45 dBm")
                            signal_part = line.split('Signal level=')[1].split()[0]
                            signal_dbm = int(signal_part.replace('dBm', ''))
                            break
                except:
                    pass

                return {
                    "connected": True,
                    "ssid": ssid,
                    "signal": signal_dbm
                }
        except:
            pass

        return {"connected": False, "ssid": None, "signal": None}

    def is_anyone_home(self):
        """
        Check if anyone is home using presence detection.

        Returns:
            bool or None: True if home, False if away, None if unavailable
        """
        if self.presence_detector is None:
            return None

        try:
            return self.presence_detector.is_anyone_home()
        except:
            return None

    def get_all_stats(self):
        """
        Get all system statistics.

        Returns:
            dict: All system information
        """
        return {
            "cpu_temp": self.get_cpu_temp(),
            "ram": self.get_ram_usage(),
            "wifi": self.get_wifi_status(),
            "is_home": self.is_anyone_home()
        }


if __name__ == "__main__":
    """Test system monitor."""
    monitor = SystemMonitor()

    print("=== Raspberry Pi System Monitor ===\n")

    stats = monitor.get_all_stats()

    print(f"CPU Temperature: {stats['cpu_temp']:.1f}°C" if stats['cpu_temp'] else "CPU Temperature: N/A")
    print(f"RAM Usage: {stats['ram']['percent']:.1f}% ({stats['ram']['used_mb']}MB / {stats['ram']['total_mb']}MB)")

    wifi = stats['wifi']
    if wifi['connected']:
        signal_str = f" ({wifi['signal']}dBm)" if wifi['signal'] else ""
        print(f"WiFi: Connected to '{wifi['ssid']}'{signal_str}")
    else:
        print("WiFi: Not connected")

    if stats['is_home'] is not None:
        print(f"Presence: {'HOME' if stats['is_home'] else 'AWAY'}")
    else:
        print("Presence: Detection not configured")
