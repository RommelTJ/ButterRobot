# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for your specifics — the stuff that's unique to your setup.

## GitLab

- Base URL: configured via `GITLAB_URL` env var on the miniPC
- Auth: `GITLAB_TOKEN` env var (Personal Access Token, stored on miniPC — never commit)
- All GitLab API calls run on the miniPC via the exec tool (curl or glab CLI)
- MR listing: `GET /api/v4/merge_requests?state=opened&scope=all`
- MR diff: `GET /api/v4/projects/:id/merge_requests/:iid/changes`
- Post comment: `POST /api/v4/projects/:id/merge_requests/:iid/notes`
- Pipeline status: `GET /api/v4/projects/:id/pipelines`

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
