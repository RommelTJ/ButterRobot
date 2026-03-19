"""ICS calendar helper — fetches and filters events from an Outlook ICS feed.

Usage:
    python -m app.calendar_helper              # Today's events as JSON
    python -m app.calendar_helper --date 2026-03-20  # Specific date
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, time
from urllib.request import urlopen

import recurring_ical_events
from icalendar import Calendar


def fetch_ics(url: str) -> Calendar:
    """Fetch and parse an ICS feed from a URL."""
    with urlopen(url, timeout=30) as resp:
        return Calendar.from_ical(resp.read())


def fetch_events(target_date: str | None = None, ics_url: str | None = None) -> list[dict]:
    """Fetch calendar events for a given date (default: today).

    Returns a list of dicts with keys:
        subject, start, end, location, is_all_day
    """
    url = ics_url or os.environ.get("CALENDAR_ICS_URL")
    if not url:
        print("Error: CALENDAR_ICS_URL must be set", file=sys.stderr)
        sys.exit(1)

    cal = fetch_ics(url)

    if target_date:
        day = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        day = datetime.now().date()

    day_start = datetime.combine(day, time.min)
    day_end = datetime.combine(day, time.max)

    events = recurring_ical_events.of(cal).between(day_start, day_end)

    result = []
    for event in events:
        dtstart = event.get("DTSTART")
        dtend = event.get("DTEND")
        start_val = dtstart.dt if dtstart else None
        end_val = dtend.dt if dtend else None

        is_all_day = isinstance(start_val, date) and not isinstance(start_val, datetime)

        result.append(
            {
                "subject": str(event.get("SUMMARY", "")),
                "start": start_val.isoformat() if start_val else "",
                "end": end_val.isoformat() if end_val else "",
                "location": str(event.get("LOCATION", "")),
                "is_all_day": is_all_day,
            }
        )

    # Sort: all-day first, then by start time
    result.sort(key=lambda e: (not e["is_all_day"], e["start"]))

    return result


def main() -> None:
    """CLI entrypoint: --date for specific day, default is today."""
    parser = argparse.ArgumentParser(description="Fetch calendar events from ICS feed")
    parser.add_argument("--date", type=str, help="Date in YYYY-MM-DD format (default: today)")

    args = parser.parse_args()

    try:
        events = fetch_events(target_date=args.date)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(events, indent=2))


if __name__ == "__main__":
    main()
