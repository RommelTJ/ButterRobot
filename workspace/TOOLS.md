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

## Execution routing

| Task                        | Runs on | Mechanism                    |
|-----------------------------|---------|------------------------------|
| GitLab API calls            | miniPC  | exec tool (curl / glab)      |
| PiAware polling             | miniPC  | exec tool (curl to dump1090) |
| Calendar queries            | miniPC  | exec tool (gcalcli or API)   |
| Cron jobs                   | miniPC  | Gateway cron scheduler       |
| IntelliJ focus / open files | MacBook | node.invoke → system.run     |
| Local git operations        | MacBook | node.invoke → system.run     |
| Manager CLI                 | MacBook | node.invoke → system.run     |
| Run local test suites       | MacBook | node.invoke → system.run     |

## Voice (ElevenLabs)

- Voice ID: `weA4Q36twV5kwSaTEL0Q`
- To apply on miniPC, update `~/.openclaw/openclaw.json`:
  - `talk.providers.elevenlabs.voiceId`
  - `messages.tts.elevenlabs.voiceId`
- Or via WebChat: `/voice set weA4Q36twV5kwSaTEL0Q`
