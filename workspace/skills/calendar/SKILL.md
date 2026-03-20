---
name: calendar
description: Fetch and summarize Office365/Outlook calendar events for status briefings and on-demand queries.
metadata: {"openclaw":{"requires":{"env":["CALENDAR_TIMEZONE"]}}}
---

# Calendar Skill

Query calendar events for status briefings and on-demand calendar questions.

## How to Fetch Events

**You MUST use this Python helper. There is no other way to get calendar data.**

```bash
# Run from /home/rommel/ButterRobot on the miniPC via exec tool

# Today's events
/home/rommel/.local/bin/uv run python -m app.calendar_helper

# Specific date
/home/rommel/.local/bin/uv run python -m app.calendar_helper --date 2026-03-20
```

Do NOT attempt to curl, wget, or fetch calendar data any other way. The helper handles
authentication, timezone conversion, and formatting. Raw calendar data is in mixed timezones
and will give you wrong times.

## Output Format

The helper outputs JSON to stdout — an array of event objects sorted by time (all-day events first).
**The start and end times are already converted to the user's local timezone (Pacific Time).**
Read them as-is — do not convert or adjust them.

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
    "start": "9 AM",
    "end": "9:30 AM",
    "location": "Zoom",
    "is_all_day": false
  },
  {
    "subject": "Product Leadership",
    "start": "1 PM",
    "end": "2 PM",
    "location": "Microsoft Teams Meeting",
    "is_all_day": false
  }
]
```

**Read the "start" field literally.** If it says "1 PM", tell the user "1 PM". If it says "10:30 AM",
tell the user "10:30 AM". Do not reinterpret, convert, or adjust the times in any way.

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
2. Filter events where start contains "PM"
3. Report only those events

### Status Briefing Integration

When giving a status briefing, lead with the calendar:
1. Fetch today's events
2. Report: "You have N meetings today. Next up is [subject] at [time]."
3. Then continue with other briefing items (MRs, etc.)

## Voice Formatting

- Lead with the next upcoming event: "Next up: Team Standup at 9 AM."
- Read times exactly as shown in the JSON — they are already in the user's timezone
- Group back-to-back meetings: "Back-to-back from 10 to noon: Design Review then Sprint Planning."
- All-day events first: "All day: Company Holiday. Plus 3 meetings."
- Keep total spoken output under 15 seconds
- Skip location unless asked
