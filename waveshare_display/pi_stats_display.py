#!/usr/bin/env python3
"""
Raspberry Pi Stats Display for Waveshare 2.13" E-Paper HAT

Displays system information (CPU temp, RAM, WiFi, presence) on e-Paper screen.
Refreshes every 30-60 seconds.
"""

import sys
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from epaper_driver import EPaperDisplay
from renderer import SystemRenderer
from system_monitor import SystemMonitor


class PiStatsDisplay:
    """Main controller for the Pi stats e-Paper display."""

    def __init__(self, config_path="config.yaml"):
        """
        Initialize the display controller.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.display_version = self.config.get("display", {}).get("version", "V3")
        self.refresh_interval = self.config.get("display", {}).get("refresh_interval", 30)

        self.epd = EPaperDisplay(version=self.display_version)
        self.renderer = SystemRenderer()
        self.monitor = SystemMonitor()

        self.running = True
        self.last_update = None
        self.update_count = 0

    def _load_config(self, config_path):
        """Load configuration from YAML file."""
        config_file = Path(config_path)

        # Try local config first
        if not config_file.exists():
            # Fall back to parent subway_train_times config
            parent_config = Path(__file__).parent.parent / "subway_train_times" / "config.yaml"
            if parent_config.exists():
                print(f"Using parent config: {parent_config}")
                config_file = parent_config
            else:
                print(f"Warning: Config file not found, using defaults")
                return {}

        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Error parsing config: {e}")
            return {}

    def update_display(self):
        """Update the display with current system stats."""
        try:
            print(f"Fetching system stats...")
            stats = self.monitor.get_all_stats()

            # Log stats
            if stats.get("cpu_temp"):
                print(f"  CPU: {stats['cpu_temp']:.1f}°C")
            print(f"  RAM: {stats['ram']['percent']:.1f}%")
            if stats['wifi']['connected']:
                print(f"  WiFi: {stats['wifi']['ssid']}")
            if stats.get("is_home") is not None:
                print(f"  Presence: {'HOME' if stats['is_home'] else 'AWAY'}")

            # Render image
            image = self.renderer.render_system_stats(stats)

            # Display (use partial refresh after first update)
            if self.update_count == 0:
                print("Full refresh (first update)")
                self.epd.display(image)
            else:
                print(f"Partial refresh (update #{self.update_count})")
                self.epd.display_partial(image)

            self.update_count += 1
            self.last_update = datetime.now()
            print(f"Display updated at {self.last_update.strftime('%I:%M:%S %p')}")

        except Exception as e:
            print(f"Error updating display: {e}")
            import traceback
            traceback.print_exc()

            # Show error on display
            try:
                error_image = self.renderer.render_error(str(e)[:50])
                self.epd.display(error_image)
            except:
                pass

    def run(self):
        """Main run loop with continuous refresh."""
        print("Starting Pi Stats Display...")
        print(f"Display version: {self.display_version}")
        print(f"Refresh interval: {self.refresh_interval} seconds")

        # Initialize display
        self.epd.init()
        print("Display initialized")

        # Initial update
        self.update_display()

        # Main loop
        try:
            while self.running:
                # Check if it's time for scheduled refresh
                if self.last_update:
                    next_update_time = self.last_update + timedelta(seconds=self.refresh_interval)

                    if datetime.now() >= next_update_time:
                        print("\n--- Scheduled refresh ---")
                        self.update_display()

                # Sleep briefly to avoid busy loop
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        print("Putting display to sleep...")
        self.epd.sleep()
        print("Cleanup complete")

    def stop(self):
        """Stop the main loop."""
        self.running = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    sys.exit(0)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Pi Stats E-Paper Display")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    parser.add_argument(
        "--version",
        choices=["V2", "V3", "V4"],
        help="Force display version (overrides config)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        help="Refresh interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Update once and exit (no continuous mode)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the display and exit"
    )

    args = parser.parse_args()

    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create display controller
    display = PiStatsDisplay(config_path=args.config)

    if args.version:
        display.display_version = args.version
        display.epd = EPaperDisplay(version=args.version)

    if args.interval:
        display.refresh_interval = args.interval

    # Handle special modes
    if args.clear:
        print("Clearing display...")
        display.epd.init()
        display.epd.clear()
        display.epd.sleep()
        print("Display cleared")
        return

    if args.once:
        print("Single update mode")
        display.epd.init()
        display.update_display()
        display.epd.sleep()
        print("Update complete")
        return

    # Run continuous mode
    display.run()


if __name__ == "__main__":
    main()
