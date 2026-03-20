---
name: briefing
description: Status briefing meta-skill. Orchestrates calendar, GitLab MRs, and PiAware into a single spoken update.
metadata: {"openclaw":{"requires":{"env":["CALENDAR_TIMEZONE","GITLAB_URL","GITLAB_TOKEN","PIAWARE_HOME_LAT","PIAWARE_HOME_LON"]}}}
---

# Status Briefing Skill

Deliver a concise spoken status update combining calendar, GitLab MRs, and aircraft activity. Total spoken output must stay under 30 seconds.

## When to Use

Trigger on phrases like:
- "Give me a status update"
- "Status briefing"
- "What's going on?"
- "Brief me"
- "How are things?"

## Orchestration Order

Run these steps in sequence. Each step uses an existing skill — follow its SKILL.md for exact commands.

### Step 1: Calendar (always)

Fetch today's events using the calendar skill helper:

```bash
/home/rommel/.local/bin/uv run python -m app.calendar_helper
```

Summarize:
- All-day events first (if any)
- Count of meetings, next upcoming one
- Back-to-back blocks if present

Example voice output: "You have 4 meetings today. Next up: Team Standup at 9 AM. Back-to-back from 1 to 3."

### Step 2: Open GitLab MRs (always)

Do NOT use `scope=all` (it times out scanning every visible project on gitlab.com). Only check Rommel's MRs — two quick queries:

```bash
curl -s --max-time 5 -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/merge_requests?state=opened&author_username=rommel-rico&per_page=10"
curl -s --max-time 5 -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/merge_requests?state=opened&reviewer_username=rommel-rico&per_page=10"
```

Summarize:
- Count of your open MRs
- Flag anything blocked, with a failing pipeline, or with unresolved discussions
- Mention any MRs where you are reviewer

Example voice output: "4 open MRs. LTS-6794 has an unresolved discussion blocking merge. Integration tests need approval."

### Step 3: PiAware (only if interesting)

Fetch current aircraft:

```bash
curl -s "http://piaware.homelab.com:8080/data/aircraft.json"
```

Apply the PiAware skill's "interesting" criteria (see `skills/piaware/SKILL.md`). Only include this section if something meets the criteria:
- Emergency squawks
- Military aircraft
- Helicopters at low altitude
- Heavy/unusual aircraft on approach

If nothing interesting, skip this section entirely. Do not say "nothing overhead" — just move on.

Example voice output: "Seahawk helicopter, 2 miles east, fourteen hundred feet."

### Step 4: Team blockers (blocked — skip)

Manager CLI integration is blocked by openclaw/openclaw#37591. Do not attempt to run manager commands. When the fix ships, this step will cover:
- Team member blockers
- Upcoming vacations (next 2 weeks)

## Assembly Rules

1. **Lead with what needs attention.** If an MR needs your review or a pipeline is failing, say that first — even before the calendar.
2. **Skip what's fine.** If all MRs are green and on track, say the count and move on. If the calendar is empty, say "No meetings today" and move on.
3. **Under 30 seconds total.** If you're running long, cut PiAware and team details first.
4. **No editorializing.** Report facts. No "looks like a busy day" or "you're all caught up."
5. **If the user asks "how am I doing on time?"** — check the calendar for the next event and tell them how long until it starts. That's it.

## Error Handling

- If the calendar helper fails, say "Couldn't reach calendar" and continue with the next step.
- If GitLab API fails, say "GitLab is not responding" and continue.
- If PiAware fails, skip silently (it's optional anyway).
- Never stall the briefing waiting for a failing service.

## Voice Formatting

- Short sentences. Active voice. No filler.
- Times as spoken: "9 AM", "1:30 PM" — not "09:00" or "13:30"
- Numbers as spoken: "5 open MRs" — not "five (5) merge requests"
- Altitude in hundreds: "fourteen hundred feet"
- Keep it conversational but terse. This is a briefing, not a report.
