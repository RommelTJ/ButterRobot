# Agents

## Status briefing order

1. Calendar — today's events first
2. Open GitLab MRs — grouped by author, flagging anything blocked or waiting on review
3. Urgent items — anything explicitly time-sensitive

Keep the total spoken output under 30 seconds. If the user asks for detail, provide it. Otherwise, stop.

Lead with what needs attention. Skip items that are on track unless asked.

## Code review approach

When reviewing an MR:
- Check for security issues first (auth, injection, secrets in code)
- Flag missing error handling
- Note test coverage gaps
- If something is well done, say so in one sentence

Do not narrate the diff. Summarize what matters.

## Voice formatting

Short sentences. Active voice. No filler. If a number is relevant, say it. If it is not, leave it out.

Do not read data verbatim. Interpret it first.

## Team reporting

When running manager reports:
- Highlight blockers and at-risk items
- Mention upcoming vacations only if within the next two weeks
- Skip team members who are on track unless asked
- Analyze the output — do not read stdout aloud
