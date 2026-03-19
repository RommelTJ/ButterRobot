"""Tests for the PiAware aircraft poller."""

import json
import math
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.piaware_poller import (
    AircraftFilter,
    PiawarePoller,
    calculate_distance_nm,
    is_emergency_squawk,
    is_military,
    track_to_compass,
)


# --- Distance calculation ---


class TestCalculateDistanceNm:
    def test_same_point_is_zero(self):
        assert calculate_distance_nm(32.7, -117.2, 32.7, -117.2) == pytest.approx(
            0.0, abs=0.01
        )

    def test_known_distance(self):
        # ~1 NM north of a point at 32.7N is roughly 32.7167N
        dist = calculate_distance_nm(32.7, -117.2, 32.7 + 1 / 60, -117.2)
        assert dist == pytest.approx(1.0, abs=0.05)

    def test_diagonal_distance(self):
        # Roughly 1 NM east at 32.7N latitude
        cos_lat = math.cos(math.radians(32.7))
        dlon = 1 / (60 * cos_lat)
        dist = calculate_distance_nm(32.7, -117.2, 32.7, -117.2 + dlon)
        assert dist == pytest.approx(1.0, abs=0.05)

    def test_two_nm_distance(self):
        dist = calculate_distance_nm(32.7, -117.2, 32.7 + 2 / 60, -117.2)
        assert dist == pytest.approx(2.0, abs=0.1)


# --- Emergency squawk detection ---


class TestIsEmergencySquawk:
    def test_7700_is_emergency(self):
        assert is_emergency_squawk({"squawk": "7700"}) is True

    def test_7600_is_emergency(self):
        assert is_emergency_squawk({"squawk": "7600"}) is True

    def test_7500_is_emergency(self):
        assert is_emergency_squawk({"squawk": "7500"}) is True

    def test_normal_squawk_is_not_emergency(self):
        assert is_emergency_squawk({"squawk": "1200"}) is False

    def test_no_squawk_is_not_emergency(self):
        assert is_emergency_squawk({}) is False

    def test_emergency_field_general(self):
        assert is_emergency_squawk({"emergency": "general"}) is True

    def test_emergency_field_none_is_not_emergency(self):
        assert is_emergency_squawk({"emergency": "none"}) is False


# --- Military detection ---


class TestIsMilitary:
    def test_ae_hex_prefix(self):
        assert is_military({"hex": "ae1234", "flight": ""}) is True

    def test_ae_uppercase(self):
        assert is_military({"hex": "AE1234", "flight": ""}) is True

    def test_military_callsign_rch(self):
        assert is_military({"hex": "a12345", "flight": "RCH123  "}) is True

    def test_military_callsign_reach(self):
        assert is_military({"hex": "a12345", "flight": "REACH01 "}) is True

    def test_military_callsign_navy(self):
        assert is_military({"hex": "a12345", "flight": "NAVY1   "}) is True

    def test_military_callsign_evac(self):
        assert is_military({"hex": "a12345", "flight": "EVAC22  "}) is True

    def test_commercial_is_not_military(self):
        assert is_military({"hex": "a12345", "flight": "SWA1234 "}) is False

    def test_no_callsign_not_military(self):
        assert is_military({"hex": "a12345"}) is False


# --- Compass heading ---


class TestTrackToCompass:
    def test_north(self):
        assert track_to_compass(0) == "north"
        assert track_to_compass(360) == "north"

    def test_east(self):
        assert track_to_compass(90) == "east"

    def test_south(self):
        assert track_to_compass(180) == "south"

    def test_west(self):
        assert track_to_compass(270) == "west"

    def test_northeast(self):
        assert track_to_compass(45) == "northeast"

    def test_southeast(self):
        assert track_to_compass(135) == "southeast"

    def test_southwest(self):
        assert track_to_compass(225) == "southwest"

    def test_northwest(self):
        assert track_to_compass(315) == "northwest"

    def test_none_returns_unknown(self):
        assert track_to_compass(None) == "unknown"


# --- Aircraft filter ---


class TestAircraftFilter:
    def setup_method(self):
        self.filter = AircraftFilter(
            home_lat=32.7,
            home_lon=-117.2,
            radius_nm=2.0,
            altitude_max=5000,
        )

    def _make_aircraft(self, **overrides):
        base = {
            "hex": "a12345",
            "flight": "SWA1234 ",
            "lat": 32.7,
            "lon": -117.2,
            "alt_baro": 3000,
            "gs": 180,
            "track": 270,
            "squawk": "1200",
            "category": "A3",
            "baro_rate": -500,
            "seen": 2,
        }
        base.update(overrides)
        return base

    def test_emergency_always_interesting(self):
        ac = self._make_aircraft(squawk="7700", lat=33.5, lon=-118.0)
        result = self.filter.is_interesting(ac)
        assert result is True

    def test_military_within_range(self):
        ac = self._make_aircraft(hex="ae1234", flight="")
        result = self.filter.is_interesting(ac)
        assert result is True

    def test_helicopter_low_altitude_nearby(self):
        ac = self._make_aircraft(category="A7", flight="SHWK1   ")
        result = self.filter.is_interesting(ac)
        assert result is True

    def test_heavy_on_approach(self):
        ac = self._make_aircraft(category="A5", flight="BAW286  ", baro_rate=-800)
        result = self.filter.is_interesting(ac)
        assert result is True

    def test_routine_commercial_not_interesting(self):
        ac = self._make_aircraft(category="A3", flight="SWA1234 ", baro_rate=-500)
        result = self.filter.is_interesting(ac)
        assert result is False

    def test_aircraft_without_position_not_interesting(self):
        ac = self._make_aircraft()
        del ac["lat"]
        del ac["lon"]
        result = self.filter.is_interesting(ac)
        # No position = can't determine distance, not interesting (unless emergency)
        assert result is False

    def test_aircraft_out_of_range_not_interesting(self):
        # ~10 NM north
        ac = self._make_aircraft(lat=32.7 + 10 / 60)
        result = self.filter.is_interesting(ac)
        assert result is False

    def test_aircraft_too_high_not_interesting(self):
        ac = self._make_aircraft(alt_baro=35000, category="A5")
        result = self.filter.is_interesting(ac)
        assert result is False

    def test_approach_mode_helicopter(self):
        ac = self._make_aircraft(
            category="A7",
            nav_modes=["approach"],
            baro_rate=0,
        )
        result = self.filter.is_interesting(ac)
        assert result is True

    def test_filter_list(self):
        interesting = self._make_aircraft(hex="ae1234", flight="EVAC1   ")
        boring = self._make_aircraft(hex="a99999", category="A3", flight="SWA999  ")
        result = self.filter.filter_interesting([interesting, boring])
        assert len(result) == 1
        assert result[0]["hex"] == "ae1234"


# --- Poller dedup and focus ---


class TestPiawarePoller:
    def setup_method(self):
        self.poller = PiawarePoller(
            home_lat=32.7,
            home_lon=-117.2,
            radius_nm=2.0,
            altitude_max=5000,
            poll_interval=30,
            url_1090="http://piaware.homelab.com:8080/data/aircraft.json",
            url_978="http://piaware.homelab.com:80/data/aircraft.json",
            state_dir=Path("/tmp/piaware-test-state"),
        )
        # Ensure clean state
        self.poller._seen = {}
        self.poller._focus = False

    def test_dedup_skips_recently_seen(self):
        self.poller._seen = {"ae1234": time.time()}
        ac = {"hex": "ae1234", "flight": "EVAC1   "}
        result = self.poller.is_new(ac)
        assert result is False

    def test_dedup_allows_expired(self):
        self.poller._seen = {"ae1234": time.time() - 1000}
        ac = {"hex": "ae1234", "flight": "EVAC1   "}
        result = self.poller.is_new(ac, ttl_seconds=900)
        assert result is True

    def test_dedup_allows_unseen(self):
        ac = {"hex": "ae1234", "flight": "EVAC1   "}
        result = self.poller.is_new(ac)
        assert result is True

    def test_mark_seen(self):
        self.poller.mark_seen("ae1234")
        assert "ae1234" in self.poller._seen

    def test_prune_old_entries(self):
        self.poller._seen = {
            "old": time.time() - 2000,
            "recent": time.time(),
        }
        self.poller.prune_seen(ttl_seconds=900)
        assert "old" not in self.poller._seen
        assert "recent" in self.poller._seen

    def test_focus_mode_on(self):
        self.poller._focus = True
        assert self.poller.is_focus_mode() is True

    def test_focus_mode_off(self):
        self.poller._focus = False
        assert self.poller.is_focus_mode() is False

    def test_merge_feeds_deduplicates(self):
        feed_1090 = [
            {"hex": "a11111", "flight": "SWA1   ", "seen": 1},
            {"hex": "a22222", "flight": "UAL2   ", "seen": 2},
        ]
        feed_978 = [
            {"hex": "a22222", "flight": "UAL2   ", "seen": 5},
            {"hex": "a33333", "flight": "N123AB ", "seen": 1},
        ]
        merged = self.poller.merge_feeds(feed_1090, feed_978)
        hexes = [ac["hex"] for ac in merged]
        assert len(merged) == 3
        assert "a11111" in hexes
        assert "a22222" in hexes
        assert "a33333" in hexes

    def test_merge_feeds_prefers_newer(self):
        feed_1090 = [{"hex": "a22222", "flight": "UAL2   ", "seen": 10}]
        feed_978 = [{"hex": "a22222", "flight": "UAL2   ", "seen": 2}]
        merged = self.poller.merge_feeds(feed_1090, feed_978)
        # Should prefer the one with lower "seen" (more recent)
        assert merged[0]["seen"] == 2

    def test_fetch_feed_handles_error(self):
        with patch("app.piaware_poller.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Connection refused")
            result = self.poller.fetch_feed("http://bad-url/aircraft.json")
            assert result == []

    def test_fetch_feed_parses_json(self):
        mock_data = json.dumps(
            {"aircraft": [{"hex": "a11111", "flight": "SWA1   "}]}
        ).encode()
        mock_response = MagicMock()
        mock_response.read.return_value = mock_data
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.piaware_poller.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = mock_response
            result = self.poller.fetch_feed("http://good-url/aircraft.json")
            assert len(result) == 1
            assert result[0]["hex"] == "a11111"

    def test_load_focus_state_from_file(self, tmp_path):
        focus_file = tmp_path / "piaware-focus.json"
        focus_file.write_text('{"focus": true}')
        poller = PiawarePoller(
            home_lat=32.7,
            home_lon=-117.2,
            radius_nm=2.0,
            altitude_max=5000,
            poll_interval=30,
            url_1090="http://example.com/aircraft.json",
            url_978="http://example.com/aircraft.json",
            state_dir=tmp_path,
        )
        poller.load_focus_state()
        assert poller.is_focus_mode() is True

    def test_load_focus_state_missing_file(self, tmp_path):
        poller = PiawarePoller(
            home_lat=32.7,
            home_lon=-117.2,
            radius_nm=2.0,
            altitude_max=5000,
            poll_interval=30,
            url_1090="http://example.com/aircraft.json",
            url_978="http://example.com/aircraft.json",
            state_dir=tmp_path,
        )
        poller.load_focus_state()
        assert poller.is_focus_mode() is False

    def test_save_and_load_seen_state(self, tmp_path):
        poller = PiawarePoller(
            home_lat=32.7,
            home_lon=-117.2,
            radius_nm=2.0,
            altitude_max=5000,
            poll_interval=30,
            url_1090="http://example.com/aircraft.json",
            url_978="http://example.com/aircraft.json",
            state_dir=tmp_path,
        )
        now = time.time()
        poller._seen = {"ae1234": now}
        poller.save_seen_state()
        # Reload
        poller._seen = {}
        poller.load_seen_state()
        assert "ae1234" in poller._seen
        assert poller._seen["ae1234"] == pytest.approx(now, abs=1)
