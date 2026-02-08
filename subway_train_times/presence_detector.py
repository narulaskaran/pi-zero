#!/usr/bin/env python3
"""
Presence Detector - Detects device presence on local network
Supports multiple detection methods with 30-second caching and grace period
"""

import subprocess
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


class PresenceDetector:
    """
    Detects device presence on local network using various methods.

    Supports:
    - arp-scan method (fast, requires sudo)
    - dhcp-leases method (slower, no sudo required)
    - 30-second result caching
    - 10-minute grace period (stays "home" after last detection)
    - Graceful error handling with fail-open behavior
    """

    def __init__(self, mac_addresses=None, cache_duration=30, grace_period_seconds=600):
        """
        Initialize presence detector.

        Args:
            mac_addresses: List of MAC addresses to detect (e.g., ["aa:bb:cc:dd:ee:ff"])
            cache_duration: Cache duration in seconds (default 30)
            grace_period_seconds: Grace period after last detection (default 600 = 10 minutes)
        """
        self.mac_addresses = [mac.lower() for mac in (mac_addresses or [])]
        self.cache_duration = cache_duration
        self.grace_period_seconds = grace_period_seconds
        self._cached_result = None
        self._cache_timestamp = None
        self._last_seen_at = None

        logger.info(f"PresenceDetector initialized with {len(self.mac_addresses)} MAC addresses, "
                   f"{cache_duration}s cache, {grace_period_seconds}s grace period")

    def is_anyone_home(self):
        """
        Check if any configured device is present on the network.
        Uses cached result if available and not expired.
        Implements 10-minute grace period after last detection.

        Returns:
            bool: True if any device is detected (or within grace period), False otherwise
        Raises:
            Exception: If detection fails outside of grace period (caller should fail-open)
        """
        # Return cached result if valid
        if self._is_cache_valid():
            logger.debug(f"Using cached presence result: {self._cached_result}")
            return self._cached_result

        # No MAC addresses configured - always return False
        if not self.mac_addresses:
            logger.warning("No MAC addresses configured for presence detection")
            return False

        # Try detection methods in order of preference
        try:
            result = self._detect_presence()

            if result:
                # Devices found! Update last seen timestamp
                self._last_seen_at = datetime.now()
                logger.info(f"✓ Devices detected on network (last_seen updated)")
            else:
                # No devices found - check grace period
                if self._is_within_grace_period():
                    grace_remaining = self._get_grace_period_remaining()
                    logger.info(f"✓ No devices found, but within grace period "
                              f"({grace_remaining:.0f}s remaining) - assuming HOME")
                    result = True
                else:
                    logger.info(f"✗ No devices found and outside grace period - assuming AWAY")

            # Cache the result
            self._cached_result = result
            self._cache_timestamp = datetime.now()

            return result

        except Exception as e:
            # Detection failed - check grace period before giving up
            if self._is_within_grace_period():
                grace_remaining = self._get_grace_period_remaining()
                logger.warning(f"⚠ Detection failed ({e}), but within grace period "
                             f"({grace_remaining:.0f}s remaining) - assuming HOME")
                # Cache True and return it
                self._cached_result = True
                self._cache_timestamp = datetime.now()
                return True
            else:
                # Outside grace period - let caller handle fail-open
                logger.error(f"✗ Detection failed ({e}) and outside grace period - raising exception")
                raise

    def _is_cache_valid(self):
        """Check if cached result is still valid."""
        if self._cached_result is None or self._cache_timestamp is None:
            return False

        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self.cache_duration

    def _is_within_grace_period(self):
        """Check if we're within the grace period of last detection."""
        if self._last_seen_at is None:
            return False

        elapsed = (datetime.now() - self._last_seen_at).total_seconds()
        return elapsed < self.grace_period_seconds

    def _get_grace_period_remaining(self):
        """Get remaining grace period time in seconds."""
        if self._last_seen_at is None:
            return 0

        elapsed = (datetime.now() - self._last_seen_at).total_seconds()
        remaining = self.grace_period_seconds - elapsed
        return max(0, remaining)

    def _detect_presence(self):
        """
        Attempt to detect presence using available methods.

        Returns:
            bool: True if any device detected, False otherwise
        Raises:
            Exception: If all detection methods fail
        """
        last_error = None

        # Try arp-scan first (fast, accurate, requires sudo)
        try:
            logger.debug("Trying arp-scan method...")
            result = self._check_arp_scan()
            if result is not None:
                logger.debug(f"arp-scan result: {result}")
                return result
            logger.debug("arp-scan returned None (command failed)")
        except Exception as e:
            logger.debug(f"arp-scan raised exception: {e}")
            last_error = e

        # Try dhcp-leases as fallback (no sudo required)
        try:
            logger.debug("Trying dhcp-leases method...")
            result = self._check_dhcp_leases()
            if result is not None:
                logger.debug(f"dhcp-leases result: {result}")
                return result
            logger.debug("dhcp-leases returned None (no lease file found)")
        except Exception as e:
            logger.debug(f"dhcp-leases raised exception: {e}")
            last_error = e

        # All methods failed - raise the last error
        if last_error:
            raise last_error
        else:
            raise Exception("All detection methods failed (returned None)")

    def _check_arp_scan(self):
        """
        Check presence using arp-scan (requires sudo).

        Returns:
            bool or None: True if detected, False if not detected, None if method failed
        """
        try:
            # Run arp-scan on local network
            logger.debug("Running: sudo arp-scan --localnet --quiet")
            result = subprocess.run(
                ["sudo", "arp-scan", "--localnet", "--quiet"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.debug(f"arp-scan failed with return code {result.returncode}")
                return None  # Command failed

            # Check if any MAC address is in the output
            output_lower = result.stdout.lower()
            found_macs = []
            for mac in self.mac_addresses:
                if mac in output_lower:
                    found_macs.append(mac)

            if found_macs:
                logger.debug(f"arp-scan found MACs: {', '.join(found_macs)}")
                return True
            else:
                logger.debug(f"arp-scan completed but found none of {len(self.mac_addresses)} configured MACs")
                return False

        except subprocess.TimeoutExpired:
            logger.debug("arp-scan timed out after 5 seconds")
            return None
        except FileNotFoundError:
            logger.debug("arp-scan command not found")
            return None
        except PermissionError:
            logger.debug("arp-scan permission denied (sudo not configured?)")
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
                    logger.debug(f"Found DHCP lease file: {path}")
                    break

            if not lease_file:
                logger.debug("No DHCP lease file found")
                return None  # No lease file found

            # Read lease file
            content = lease_file.read_text().lower()

            # Check if any MAC address is in the lease file
            found_macs = []
            for mac in self.mac_addresses:
                if mac in content:
                    found_macs.append(mac)

            if found_macs:
                logger.debug(f"dhcp-leases found MACs: {', '.join(found_macs)}")
                return True
            else:
                logger.debug(f"dhcp-leases checked but found none of {len(self.mac_addresses)} configured MACs")
                return False

        except IOError as e:
            logger.debug(f"dhcp-leases IO error: {e}")
            return None
        except PermissionError as e:
            logger.debug(f"dhcp-leases permission error: {e}")
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
