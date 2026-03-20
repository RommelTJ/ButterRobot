---
name: manager
description: Natural language interface to the Typer-based manager CLI on the MacBook. Team reports, 1-1 prep, code stats, vacations, goals.
metadata: {}
---

# Manager CLI Skill

Interface with the manager CLI — a Typer-based tool on the MacBook for team management data. All commands are
read-only. The CLI runs on the MacBook via `node.invoke → system.run`.

## Execution

All commands run on the MacBook. Use `node.invoke → system.run` with this pattern:

```
cd /Users/rommel/code/work/chatmeter/manager && uv run python manager_cli.py <command>
```

The MacBook must be connected to the gateway. If the node is unreachable, tell the user: "Can't reach the MacBook
right now."

## Team Members

- **Adam** — software engineer
- **Fele** — software engineer
- **Mitchell** — software engineer
- **Rommel** — engineering manager (the user)

Name resolution: the CLI accepts first names (case-insensitive). "Mitch" won't work — use "Mitchell".

## Command Reference

### Team Overview

| Command | Trigger examples | What it returns |
|---------|-----------------|-----------------|
| `report` | "team report", "how's the team?", "status briefing" | Full team report with blockers, PRs, activity |
| `projects list` | "active projects?", "what's the team working on?" | List of active projects with assignees |
| `events team [--weeks N]` | "what happened this week?", "team events" | Team events/activity for the past N weeks (default 1) |

### Individual — 1-1 Prep

| Command | Trigger examples | What it returns |
|---------|-----------------|-----------------|
| `prep <name>` | "how's Mitchell doing?", "prep for 1-1 with Fele" | 1-1 prep: recent activity, PRs, notes, goals |
| `events list [employee]` | "Mitchell's events", "what has Adam been up to?" | Individual event history |

### Code Activity

| Command | Trigger examples | What it returns |
|---------|-----------------|-----------------|
| `code stats [--weeks N]` | "code velocity", "merge stats" | Team code stats for past N weeks |
| `code trends [employee]` | "Adam's coding trends", "Fele's velocity" | Code trend data for an individual |
| `code history <employee>` | "what has Mitchell been merging?" | Recent merge history for an individual |
| `code team` | "team code activity", "who's been shipping?" | Team-wide code activity summary |

### Vacations / PTO

| Command | Trigger examples | What it returns |
|---------|-----------------|-----------------|
| `vacation list [employee] [--days N]` | "when is Fele on vacation?", "upcoming PTO" | Vacation schedule (next N days, default 30) |
| `vacation stats` | "PTO usage", "how much vacation has everyone taken?" | PTO usage statistics |

### People & Goals

| Command | Trigger examples | What it returns |
|---------|-----------------|-----------------|
| `employee list` | "who's on the team?" | List of all team members |
| `employee show <name>` | "tell me about Adam" | Employee details |
| `goals list <employee>` | "Fele's goals", "what are Mitchell's goals?" | Individual goals and progress |

### Notes

| Command | Trigger examples | What it returns |
|---------|-----------------|-----------------|
| `notes list <employee>` | "notes on Mitchell", "my notes about Fele" | Stored notes for an employee |
| `notes search "keyword"` | "search notes for performance" | Search across all notes |

### Annual Reviews

| Command | Trigger examples | What it returns |
|---------|-----------------|-----------------|
| `annual report <employee>` | "annual review data for Adam" | Individual annual review data |
| `annual team-report` | "team annual review", "yearly summary" | Team-wide annual review data |

## Output Handling

The CLI uses Rich formatting (tables, colors, panels). When capturing output via `system.run`:

- The output may contain ANSI escape codes — ignore them and parse the text content
- Extract key data points (blockers, metrics, dates) from the structured text
- Summarize for voice — don't relay raw CLI output verbatim
- Long outputs (annual reports) should be heavily summarized — focus on highlights and concerns

## Common Workflows

### Status Briefing (team report)

1. Run `report`
2. Lead with blockers or concerns
3. Mention anyone with stale PRs or low activity
4. Skip people who are on track unless asked

### 1-1 Prep

1. Run `prep <name>`
2. Summarize: recent PRs, any blockers, goal progress, upcoming PTO
3. Suggest talking points if anything stands out

### Vacation Check

1. Run `vacation list` (all) or `vacation list <name>` (individual)
2. Report upcoming dates concisely

### Code Velocity

1. Run `code stats` for team overview
2. If user asks about a specific person, follow up with `code trends <name>`

## Voice Formatting

- Lead with concerns or blockers — good news can wait
- Skip people who are on-track unless the user asks about them specifically
- Under 30 seconds for team reports
- Under 20 seconds per person for 1-1 prep
- Use natural language: "Mitchell has 3 open MRs, oldest is 4 days" not raw stats
- For vacations: "Fele is out next Thursday and Friday"

## Boundaries

This skill is **read-only**. If the user asks to:
- Add a note → suggest: "You can add that directly with `notes add <name> 'note text'`"
- Update goals → suggest: "Run `goals update <name>` from the terminal"
- Modify any data → explain it's read-only and suggest the direct CLI command

Never run write commands through the agent.
