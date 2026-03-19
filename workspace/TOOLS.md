# Tools

## GitLab

- Base URL: configured via `GITLAB_URL` env var on the miniPC
- Auth: `GITLAB_TOKEN` env var (Personal Access Token, stored on miniPC — never commit)
- All GitLab API calls run on the miniPC via the exec tool (curl or glab CLI)
- MR listing: `GET /api/v4/merge_requests?state=opened&scope=all`
- MR diff: `GET /api/v4/projects/:id/merge_requests/:iid/changes`
- Post comment: `POST /api/v4/projects/:id/merge_requests/:iid/notes`
- Pipeline status: `GET /api/v4/projects/:id/pipelines`

## Execution routing

| Task | Runs on | Mechanism |
|------|---------|-----------|
| GitLab API calls | miniPC | exec tool (curl / glab) |
| PiAware polling | miniPC | exec tool (curl to dump1090) |
| Calendar queries | miniPC | exec tool (gcalcli or API) |
| Cron jobs | miniPC | Gateway cron scheduler |
| IntelliJ focus / open files | MacBook | node.invoke → system.run |
| Local git operations | MacBook | node.invoke → system.run |
| Manager CLI | MacBook | node.invoke → system.run |
| Run local test suites | MacBook | node.invoke → system.run |

## MR review standards

- Flag: security issues, unhandled errors, missing test coverage, hardcoded secrets
- Note: breaking changes, missing documentation on public interfaces
- Approve with note when the MR is clean but minor suggestions remain

## Voice (ElevenLabs)

<!-- TODO: Sample Rick and Morty voices in the ElevenLabs Voice Library
     (https://elevenlabs.io/app/voice-library) and update the following:

     On miniPC: ~/.openclaw/openclaw.json
       - talk.providers.elevenlabs.voiceId
       - messages.tts.elevenlabs.voiceId

     Or via WebChat: /voice set [name or id]

     Candidates to try: search "Rick Sanchez", "Rick and Morty", "robot"
     No public Butter Robot voice found — may need ElevenLabs Instant Voice Clone
     from episode audio clips. Fish Audio has two Rick Sanchez models as fallback:
       - https://fish.audio/m/d2e75a3e3fd6419893057c02a375a113/
       - https://fish.audio/m/6d90f8435d8845db852174d5fecb42c0/
-->
