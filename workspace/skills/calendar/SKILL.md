---
name: calendar
description: Fetch and summarize Office365/Outlook calendar events from a published ICS feed for status briefings and on-demand queries.
metadata: {"openclaw":{"requires":{"env":["CALENDAR_ICS_URL","CALENDAR_TIMEZONE"]}}}
---

# Calendar Skill

Query Office365/Outlook calendar events via a published ICS feed. Used for status briefings and on-demand
calendar questions.

## Data Source

A published ICS URL from Outlook. Set as `CALENDAR_ICS_URL` in the gateway environment.
Event times in the ICS feed may be in different timezones (e.g. Mountain Time).
The helper converts all times to `CALENDAR_TIMEZONE` (default: `America/Los_Angeles`).

**IMPORTANT**: Always use the Python helper below to fetch events. Never curl the ICS URL directly — the raw
ICS contains times in the organizer's timezone, not the user's. The helper handles timezone conversion.

## Commands

All commands run on the miniPC via the exec tool from `/home/rommel/ButterRobot`:

```bash
# Today's events
uv run python -m app.calendar_helper

# Specific date
uv run python -m app.calendar_helper --date 2026-03-20
```

## Output Format

The helper outputs JSON to stdout — an array of event objects sorted by time (all-day events first):

```json
[
  {
    "subject": "Company Holiday",
    "start": "2026-03-19",
    "end": "2026-03-20",
    "location": "",
    "is_all_day": true
  },
  {
    "subject": "Team Standup",
    "start": "2026-03-19T09:00:00",
    "end": "2026-03-19T09:30:00",
    "location": "Zoom",
    "is_all_day": false
  }
]
```

Errors go to stderr with exit code 1.

## Common Workflows

### "What's on my calendar?" / "Any meetings today?"

1. Run the helper with no args (defaults to today)
2. Summarize: count of meetings, next upcoming one, any gaps

### "Anything tomorrow?" / "What about Friday?"

1. Run the helper with `--date YYYY-MM-DD`
2. Summarize the day

### "Any meetings this afternoon?"

1. Run the helper for today
2. Filter events with start time after 12:00
3. Report only afternoon events

### Status Briefing Integration

When giving a status briefing, lead with the calendar:
1. Fetch today's events
2. Report: "You have N meetings today. Next up is [subject] at [time]."
3. Then continue with other briefing items (MRs, etc.)

## Voice Formatting

- Lead with the next upcoming event: "Next up: Team Standup at 9."
- Use natural times: "9", "2:30", "noon" — not "09:00:00"
- Group back-to-back meetings: "Back-to-back from 10 to noon: Design Review then Sprint Planning."
- All-day events first: "All day: Company Holiday. Plus 3 meetings."
- Keep total spoken output under 15 seconds
- Skip location unless asked
