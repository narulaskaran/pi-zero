#!/usr/bin/env python3
"""
Presence Detector - Detects device presence on local network
Supports multiple detection methods with 30-second caching
"""

import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path


class PresenceDetector:
    """
    Detects device presence on local network using various methods.

    Supports:
    - arp-scan method (fast, requires sudo)
    - dhcp-leases method (slower, no sudo required)
    - 30-second result caching
    - Graceful error handling
    """

    def __init__(self, mac_addresses=None, cache_duration=30):
        """
        Initialize presence detector.

        Args:
            mac_addresses: List of MAC addresses to detect (e.g., ["aa:bb:cc:dd:ee:ff"])
            cache_duration: Cache duration in seconds (default 30)
        """
        self.mac_addresses = [mac.lower() for mac in (mac_addresses or [])]
        self.cache_duration = cache_duration
        self._cached_result = None
        self._cache_timestamp = None

    def is_anyone_home(self):
        """
        Check if any configured device is present on the network.
        Uses cached result if available and not expired.

        Returns:
            bool: True if any device is detected, False otherwise
        """
        # Return cached result if valid
        if self._is_cache_valid():
            return self._cached_result

        # No MAC addresses configured - always return False
        if not self.mac_addresses:
            return False

        # Try detection methods in order of preference
        result = self._detect_presence()

        # Cache the result
        self._cached_result = result
        self._cache_timestamp = datetime.now()

        return result

    def _is_cache_valid(self):
        """Check if cached result is still valid."""
        if self._cached_result is None or self._cache_timestamp is None:
            return False

        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self.cache_duration

    def _detect_presence(self):
        """
        Attempt to detect presence using available methods.

        Returns:
            bool: True if any device detected, False otherwise
        """
        # Try arp-scan first (fast, accurate, requires sudo)
        try:
            result = self._check_arp_scan()
            if result is not None:
                return result
        except Exception:
            pass  # Fall through to next method

        # Try dhcp-leases as fallback (no sudo required)
        try:
            result = self._check_dhcp_leases()
            if result is not None:
                return result
        except Exception:
            pass

        # All methods failed - assume not present
        return False

    def _check_arp_scan(self):
        """
        Check presence using arp-scan (requires sudo).

        Returns:
            bool or None: True if detected, False if not detected, None if method failed
        """
        try:
            # Run arp-scan on local network
            result = subprocess.run(
                ["sudo", "arp-scan", "--localnet", "--quiet"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None  # Command failed

            # Check if any MAC address is in the output
            output_lower = result.stdout.lower()
            for mac in self.mac_addresses:
                if mac in output_lower:
                    return True

            return False

        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            return None

    def _check_dhcp_leases(self):
        """
        Check presence using DHCP leases file (no sudo required).

        Returns:
            bool or None: True if detected, False if not detected, None if method failed
        """
        # Common DHCP lease file locations
        lease_paths = [
            "/var/lib/dhcp/dhcpd.leases",
            "/var/lib/dhcpd/dhcpd.leases",
            "/var/db/dhcpd.leases",
        ]

        try:
            # Find the first existing lease file
            lease_file = None
            for path in lease_paths:
                if Path(path).exists():
                    lease_file = Path(path)
                    break

            if not lease_file:
                return None  # No lease file found

            # Read lease file
            content = lease_file.read_text().lower()

            # Check if any MAC address is in the lease file
            for mac in self.mac_addresses:
                if mac in content:
                    return True

            return False

        except (IOError, PermissionError):
            return None


def main():
    """Test the presence detector."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python presence_detector.py <mac_address> [mac_address ...]")
        print("Example: python presence_detector.py aa:bb:cc:dd:ee:ff 11:22:33:44:55:66")
        sys.exit(1)

    detector = PresenceDetector(mac_addresses=sys.argv[1:])

    print(f"Detecting presence for MAC addresses: {', '.join(detector.mac_addresses)}")
    print(f"Cache duration: {detector.cache_duration} seconds")
    print()

    # First check
    print("First check:")
    result = detector.is_anyone_home()
    print(f"  Result: {result}")
    print(f"  Cache timestamp: {detector._cache_timestamp}")
    print()

    # Immediate second check (should use cache)
    print("Immediate second check (should use cache):")
    result = detector.is_anyone_home()
    print(f"  Result: {result}")
    print(f"  Cache timestamp: {detector._cache_timestamp}")
    print()


if __name__ == "__main__":
    main()
