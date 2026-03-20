# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for your specifics — the stuff that's unique to your setup.

## GitLab

- Skills: see `skills/gitlab/SKILL.md` for GitLab MR operations
- Base URL: configured via `GITLAB_URL` env var on the miniPC
- Auth: `GITLAB_TOKEN` env var (Personal Access Token, stored on miniPC — never commit)
- All GitLab API calls run on the miniPC via the exec tool (curl or glab CLI)

## PiAware

- Skill: see `skills/piaware/SKILL.md` for aircraft tracking operations
- Data source: PiAware receiver on LAN (dump1090-fa 1090MHz + skyaware978 UAT)
- Home position: `$PIAWARE_HOME_LAT` / `$PIAWARE_HOME_LON` env vars (never hardcode)
- Proactive alerts: Python poller script filters locally, invokes agent only for interesting aircraft
- Focus mode: `workspace/state/piaware-focus.json` — toggle via voice ("focus mode on/off")

## Calendar

- Skill: see `skills/calendar/SKILL.md` for calendar event queries
- Helper script: `app/calendar_helper.py` — fetches published ICS feed, filters by date, outputs JSON
- No OAuth — uses a published ICS URL from Outlook (contains a secret token, never commit)
- Env var: `CALENDAR_ICS_URL` (set in gateway systemd env)
- Runs on miniPC via exec tool: `uv run python -m app.calendar_helper [--date YYYY-MM-DD]`

## Execution routing

| Task                        | Runs on | Mechanism                       |
|-----------------------------|---------|-------------------------------- |
| GitLab API calls            | miniPC  | exec tool (curl / glab)         |
| PiAware polling             | miniPC  | exec tool (curl to dump1090)    |
| Calendar queries            | miniPC  | exec tool (python helper)       |
| Cron jobs                   | miniPC  | Gateway cron scheduler          |

## Known Limitations — macOS Node Exec

The OpenClaw macOS companion app does **not** support `system.run` as of v2026.3.14
([openclaw/openclaw#37591](https://github.com/openclaw/openclaw/issues/37591)).
The node advertises browser, canvas, and screen capabilities only. All skills must
run on the miniPC via the exec tool. No shell commands can be routed to the MacBook.

**When the fix ships:** re-add the manager skill from git history (commit `924575d`)
and configure `tools.exec.host=node` + `tools.exec.node="Rommel's MacBook Pro"` in
the gateway config.

## Voice (ElevenLabs)

- Voice ID: `weA4Q36twV5kwSaTEL0Q`
- To apply on miniPC, update `~/.openclaw/openclaw.json`:
  - `talk.providers.elevenlabs.voiceId`
  - `messages.tts.elevenlabs.voiceId`
- Or via WebChat: `/voice set weA4Q36twV5kwSaTEL0Q`
