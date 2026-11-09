"""Deterministic adaptive refresh-policy tests; no network or device access."""
import hashlib
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import subway_server as server


class RefreshPolicyTests(unittest.TestCase):
    def policy(self, now, presence=(True, None, False), config=None):
        if config is None:
            config = {"refresh_rate": {"night_hours": {"start": 1, "end": 7}}}
        with patch.object(server, "load_config", return_value=config), \
             patch.object(server.SharedPresenceState, "read_state", return_value=presence):
            return server.refresh_policy(now)

    def test_home_away_and_night_priority(self):
        daytime = datetime(2026, 11, 9, 12, tzinfo=server.NEW_YORK)
        self.assertEqual(self.policy(daytime, (True, None, False))[:2], (900, "home"))
        self.assertEqual(self.policy(daytime, (False, None, False))[:2], (3600, "away"))
        night = datetime(2026, 11, 9, 2, tzinfo=server.NEW_YORK)
        self.assertEqual(self.policy(night, (True, None, False))[:2], (3600, "night"))
        self.assertEqual(self.policy(night, (False, None, False))[:2], (3600, "night"))

    def test_night_start_inclusive_end_exclusive_and_overnight(self):
        cfg = {"refresh_rate": {"night_hours": {"start": 1, "end": 7}}}
        for hour, expected in ((0, "home"), (1, "night"), (6, "night"), (7, "home")):
            now = datetime(2026, 11, 9, hour, tzinfo=server.NEW_YORK)
            self.assertEqual(self.policy(now, config=cfg)[1], expected)
        overnight = {"refresh_rate": {"night_hours": {"start": 23, "end": 7}}}
        for hour, expected in ((22, "home"), (23, "night"), (0, "night"), (6, "night"), (7, "home")):
            now = datetime(2026, 11, 9, hour, tzinfo=server.NEW_YORK)
            self.assertEqual(self.policy(now, config=overnight)[1], expected)
        equal = {"refresh_rate": {"night_hours": {"start": 7, "end": 7}}}
        self.assertEqual(self.policy(datetime(2026, 11, 9, 7, tzinfo=server.NEW_YORK), config=equal)[1], "home")

    def test_utc_instants_are_evaluated_on_new_york_clock(self):
        # 05:30 UTC is 00:30 EST; 06:30 UTC is 01:30 EST.
        before = datetime(2026, 11, 9, 5, 30, tzinfo=timezone.utc)
        during = datetime(2026, 11, 9, 6, 30, tzinfo=timezone.utc)
        self.assertEqual(self.policy(before)[1], "home")
        self.assertEqual(self.policy(during)[1], "night")

    def test_stale_missing_and_read_errors_are_unknown_but_night_stays_slow(self):
        daytime = datetime(2026, 11, 9, 12, tzinfo=server.NEW_YORK)
        for state in ((True, None, True), (None, None, True), (None, None, False)):
            self.assertEqual(self.policy(daytime, state)[:2], (900, "unknown"))
        with patch.object(server, "load_config", return_value={}), \
             patch.object(server.SharedPresenceState, "read_state", side_effect=OSError("cache unavailable")):
            self.assertEqual(server.refresh_policy(daytime)[:2], (900, "unknown"))
            self.assertEqual(server.refresh_policy(datetime(2026, 11, 9, 2, tzinfo=server.NEW_YORK))[:2], (3600, "night"))

    def test_unknown_never_invokes_legacy_network_detector(self):
        now = datetime(2026, 11, 9, 12, tzinfo=server.NEW_YORK)
        with patch.object(server, "load_config", return_value={}), \
             patch.object(server.SharedPresenceState, "read_state", side_effect=OSError()), \
             patch.object(server, "get_presence_detector", side_effect=AssertionError("must not scan")) as detector:
            self.assertEqual(server.calculate_refresh_rate(now), 900)
            detector.assert_not_called()

    def test_legacy_interval_values_cannot_override_policy(self):
        config = {"refresh_rate": {
            "intervals": {"fast": 60, "slow": 1800, "night": 1800},
            "night_hours": {"start": 1, "end": 7},
        }}
        now = datetime(2026, 11, 9, 12, tzinfo=server.NEW_YORK)
        self.assertEqual(self.policy(now, (True, None, False), config)[:2], (900, "home"))
        self.assertEqual(self.policy(now, (False, None, False), config)[:2], (3600, "away"))

    def test_invalid_night_config_falls_back_and_malformed_config_is_safe(self):
        now = datetime(2026, 11, 9, 2, tzinfo=server.NEW_YORK)
        for bad in (None, "invalid", {"start": 1}, {"start": 24, "end": 7},
                    {"start": True, "end": 7}, {"start": "1", "end": 7}):
            self.assertEqual(self.policy(now, (True, None, False), {"refresh_rate": {"night_hours": bad}})[1], "night")
        with patch.object(server, "load_config", return_value=None), \
             patch.object(server.SharedPresenceState, "read_state", return_value=(True, None, False)):
            self.assertEqual(server.refresh_policy(datetime(2026, 11, 9, 12, tzinfo=server.NEW_YORK))[:2], (900, "home"))
        self.assertEqual(self.policy(now, config={"refresh_rate": "malformed"})[1], "night")

    def test_firmware_contract_and_status_report_effective_policy(self):
        client = server.app.test_client()
        with patch.object(server, "load_config", return_value={}), \
             patch.object(server.SharedPresenceState, "read_state", return_value=(False, None, False)), \
             patch.object(server.SharedPresenceState, "get_state_info", return_value={"exists": True}):
            firmware = client.get("/refresh-rate")
            self.assertEqual(firmware.status_code, 200)
            self.assertEqual(firmware.json, {"refresh_minutes": 60})
            status_response = client.get("/status")
        self.assertEqual(status_response.status_code, 200)
        status = status_response.json
        self.assertEqual(status["current_refresh_seconds"], 3600)
        self.assertEqual(status["current_refresh_minutes"], 60)
        self.assertEqual(status["configured_intervals"], {"fast": 900, "slow": 3600, "night": 3600})
        self.assertEqual(status["effective_intervals"], {"fast": 900, "slow": 3600, "night": 3600})
        self.assertEqual(status["refresh_policy_reason"], "away")
        self.assertEqual(status["refresh_policy_timezone"], "America/New_York")
        self.assertEqual(status["refresh_policy_night_hours"], {"start": 1, "end": 7})
        self.assertEqual(status["refresh_policy_version"], server.REFRESH_POLICY_VERSION)
        with open(server.__file__, "rb") as source:
            self.assertEqual(status["server_sha256"], hashlib.sha256(source.read()).hexdigest())


if __name__ == "__main__":
    unittest.main()
