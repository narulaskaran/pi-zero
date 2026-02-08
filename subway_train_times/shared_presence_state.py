#!/usr/bin/env python3
"""
Shared Presence State - Cross-process presence detection cache

This module allows Waveshare display and subway_server to share presence
detection results without duplicate arp-scans. Waveshare writes presence
state to a file every 45s, subway_server reads from it.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Shared state file location
PRESENCE_STATE_FILE = Path("/tmp/presence_state.json")
MAX_STATE_AGE_SECONDS = 120  # Consider stale after 2 minutes


class SharedPresenceState:
    """
    Manages shared presence state between processes via filesystem.

    Writer (Waveshare): Calls write_state() every 45s with detection result
    Reader (subway_server): Calls read_state() to get cached result
    """

    @staticmethod
    def write_state(is_home: bool, devices_found: list = None):
        """
        Write presence state to shared file.

        Args:
            is_home: True if devices detected, False otherwise
            devices_found: List of MAC addresses detected (optional)
        """
        try:
            state = {
                "is_home": is_home,
                "timestamp": datetime.now().isoformat(),
                "devices_found": devices_found or [],
                "writer": "waveshare_display"
            }

            # Atomic write (write to temp file, then rename)
            temp_file = PRESENCE_STATE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state, f)
            temp_file.rename(PRESENCE_STATE_FILE)

            logger.debug(f"Wrote presence state: {is_home} to {PRESENCE_STATE_FILE}")

        except Exception as e:
            logger.error(f"Failed to write presence state: {e}")

    @staticmethod
    def read_state():
        """
        Read presence state from shared file.

        Returns:
            tuple: (is_home: bool or None, timestamp: datetime or None, is_stale: bool)
            Returns (None, None, True) if file doesn't exist or is too old
        """
        try:
            if not PRESENCE_STATE_FILE.exists():
                logger.debug("Presence state file doesn't exist")
                return None, None, True

            with open(PRESENCE_STATE_FILE, 'r') as f:
                state = json.load(f)

            # Parse timestamp
            timestamp = datetime.fromisoformat(state['timestamp'])
            is_home = state['is_home']

            # Check if stale
            age = (datetime.now() - timestamp).total_seconds()
            is_stale = age > MAX_STATE_AGE_SECONDS

            if is_stale:
                logger.warning(f"Presence state is stale ({age:.0f}s old, max {MAX_STATE_AGE_SECONDS}s)")
            else:
                logger.debug(f"Read presence state: {is_home} ({age:.0f}s old)")

            return is_home, timestamp, is_stale

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse presence state file: {e}")
            return None, None, True
        except Exception as e:
            logger.error(f"Failed to read presence state: {e}")
            return None, None, True

    @staticmethod
    def get_state_info():
        """
        Get detailed state info for debugging.

        Returns:
            dict: State information including age, staleness, etc.
        """
        try:
            if not PRESENCE_STATE_FILE.exists():
                return {
                    "exists": False,
                    "error": "File doesn't exist"
                }

            with open(PRESENCE_STATE_FILE, 'r') as f:
                state = json.load(f)

            timestamp = datetime.fromisoformat(state['timestamp'])
            age = (datetime.now() - timestamp).total_seconds()

            return {
                "exists": True,
                "is_home": state['is_home'],
                "timestamp": state['timestamp'],
                "age_seconds": age,
                "is_stale": age > MAX_STATE_AGE_SECONDS,
                "devices_found": state.get('devices_found', []),
                "writer": state.get('writer', 'unknown')
            }

        except Exception as e:
            return {
                "exists": True,
                "error": str(e)
            }
