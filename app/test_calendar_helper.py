"""Tests for calendar_helper — ICS feed fetching and event filtering."""

import json
from datetime import date, datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from icalendar import Calendar, Event

from app.calendar_helper import fetch_events, main


def _make_ics_feed(*events_data) -> Calendar:
    """Build a minimal ICS Calendar with the given events."""
    cal = Calendar()
    cal.add("prodid", "-//Test//Test//EN")
    cal.add("version", "2.0")
    for ev_data in events_data:
        event = Event()
        event.add("summary", ev_data.get("summary", "Test Event"))
        event.add("dtstart", ev_data["dtstart"])
        event.add("dtend", ev_data["dtend"])
        if "location" in ev_data:
            event.add("location", ev_data["location"])
        cal.add_component(event)
    return cal


class TestFetchEvents:
    @patch("app.calendar_helper.fetch_ics")
    def test_returns_formatted_list(self, mock_fetch_ics):
        mock_fetch_ics.return_value = _make_ics_feed(
            {
                "summary": "Team Standup",
                "dtstart": datetime(2026, 3, 19, 9, 0),
                "dtend": datetime(2026, 3, 19, 9, 30),
                "location": "Zoom",
            }
        )

        result = fetch_events(target_date="2026-03-19", ics_url="https://example.com/cal.ics")

        assert len(result) == 1
        event = result[0]
        assert event["subject"] == "Team Standup"
        assert "2026-03-19" in event["start"]
        assert "2026-03-19" in event["end"]
        assert event["location"] == "Zoom"
        assert event["is_all_day"] is False

    @patch("app.calendar_helper.fetch_ics")
    def test_empty_calendar(self, mock_fetch_ics):
        mock_fetch_ics.return_value = _make_ics_feed()

        result = fetch_events(target_date="2026-03-19", ics_url="https://example.com/cal.ics")
        assert result == []

    @patch("app.calendar_helper.fetch_ics")
    def test_specific_date_filters_correctly(self, mock_fetch_ics):
        mock_fetch_ics.return_value = _make_ics_feed(
            {
                "summary": "March 19 Meeting",
                "dtstart": datetime(2026, 3, 19, 10, 0),
                "dtend": datetime(2026, 3, 19, 11, 0),
            },
            {
                "summary": "March 20 Meeting",
                "dtstart": datetime(2026, 3, 20, 10, 0),
                "dtend": datetime(2026, 3, 20, 11, 0),
            },
        )

        result = fetch_events(target_date="2026-03-20", ics_url="https://example.com/cal.ics")

        assert len(result) == 1
        assert result[0]["subject"] == "March 20 Meeting"

    @patch("app.calendar_helper.fetch_ics")
    def test_all_day_event(self, mock_fetch_ics):
        mock_fetch_ics.return_value = _make_ics_feed(
            {
                "summary": "Company Holiday",
                "dtstart": date(2026, 3, 19),
                "dtend": date(2026, 3, 20),
            }
        )

        result = fetch_events(target_date="2026-03-19", ics_url="https://example.com/cal.ics")

        assert len(result) == 1
        assert result[0]["is_all_day"] is True
        assert result[0]["subject"] == "Company Holiday"

    @patch("app.calendar_helper.fetch_ics")
    def test_all_day_events_sorted_first(self, mock_fetch_ics):
        mock_fetch_ics.return_value = _make_ics_feed(
            {
                "summary": "9am Meeting",
                "dtstart": datetime(2026, 3, 19, 9, 0),
                "dtend": datetime(2026, 3, 19, 10, 0),
            },
            {
                "summary": "All Day Event",
                "dtstart": date(2026, 3, 19),
                "dtend": date(2026, 3, 20),
            },
        )

        result = fetch_events(target_date="2026-03-19", ics_url="https://example.com/cal.ics")

        assert result[0]["subject"] == "All Day Event"
        assert result[1]["subject"] == "9am Meeting"

    @patch("app.calendar_helper.fetch_ics")
    def test_missing_location_returns_empty_string(self, mock_fetch_ics):
        mock_fetch_ics.return_value = _make_ics_feed(
            {
                "summary": "No Location Meeting",
                "dtstart": datetime(2026, 3, 19, 14, 0),
                "dtend": datetime(2026, 3, 19, 15, 0),
            }
        )

        result = fetch_events(target_date="2026-03-19", ics_url="https://example.com/cal.ics")
        assert result[0]["location"] == ""

    def test_missing_url_exits_with_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit):
                fetch_events(target_date="2026-03-19")

    @patch("app.calendar_helper.fetch_ics")
    def test_converts_to_local_timezone(self, mock_fetch_ics):
        # Event at 1 PM Mountain Time (UTC-6 during MDT)
        mountain = ZoneInfo("America/Denver")
        mock_fetch_ics.return_value = _make_ics_feed(
            {
                "summary": "Pi Day Demos",
                "dtstart": datetime(2026, 3, 20, 13, 0, tzinfo=mountain),
                "dtend": datetime(2026, 3, 20, 15, 30, tzinfo=mountain),
            }
        )

        result = fetch_events(
            target_date="2026-03-20",
            ics_url="https://example.com/cal.ics",
            tz_name="America/Los_Angeles",
        )

        assert len(result) == 1
        # 1 PM Mountain = 12 PM Pacific
        assert "T12:00:00" in result[0]["start"]
        assert "T14:30:00" in result[0]["end"]

    @patch("app.calendar_helper.fetch_ics")
    def test_respects_calendar_timezone_env(self, mock_fetch_ics):
        # Event at 3 PM UTC
        mock_fetch_ics.return_value = _make_ics_feed(
            {
                "summary": "UTC Meeting",
                "dtstart": datetime(2026, 3, 19, 15, 0, tzinfo=timezone.utc),
                "dtend": datetime(2026, 3, 19, 16, 0, tzinfo=timezone.utc),
            }
        )

        with patch.dict("os.environ", {"CALENDAR_TIMEZONE": "America/New_York"}):
            result = fetch_events(
                target_date="2026-03-19",
                ics_url="https://example.com/cal.ics",
            )

        assert len(result) == 1
        # 3 PM UTC = 11 AM EDT
        assert "T11:00:00" in result[0]["start"]

    @patch("app.calendar_helper.fetch_ics")
    def test_all_day_events_not_converted(self, mock_fetch_ics):
        mock_fetch_ics.return_value = _make_ics_feed(
            {
                "summary": "Holiday",
                "dtstart": date(2026, 3, 19),
                "dtend": date(2026, 3, 20),
            }
        )

        result = fetch_events(
            target_date="2026-03-19",
            ics_url="https://example.com/cal.ics",
            tz_name="America/Los_Angeles",
        )

        assert result[0]["is_all_day"] is True
        assert result[0]["start"] == "2026-03-19"


class TestMain:
    @patch("app.calendar_helper.fetch_events")
    @patch.dict("os.environ", {"CALENDAR_ICS_URL": "https://example.com/cal.ics"})
    def test_default_prints_json(self, mock_fetch):
        mock_fetch.return_value = [{"subject": "Meeting", "start": "2026-03-19T09:00:00"}]

        with patch("sys.argv", ["calendar_helper.py"]):
            with patch("builtins.print") as mock_print:
                main()

        mock_print.assert_called_once()
        output = mock_print.call_args[0][0]
        parsed = json.loads(output)
        assert parsed[0]["subject"] == "Meeting"

    @patch("app.calendar_helper.fetch_events")
    @patch.dict("os.environ", {"CALENDAR_ICS_URL": "https://example.com/cal.ics"})
    def test_date_flag(self, mock_fetch):
        mock_fetch.return_value = []

        with patch("sys.argv", ["calendar_helper.py", "--date", "2026-03-20"]):
            with patch("builtins.print"):
                main()

        mock_fetch.assert_called_once_with(target_date="2026-03-20")

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_env_exits_with_error(self, capsys):
        with patch("sys.argv", ["calendar_helper.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.err
