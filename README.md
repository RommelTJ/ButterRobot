# ButterRobot

**v0.3.0 — March 18, 2026**

> What is my purpose? To read your calendar, review your GitLab MRs, and tell you what's flying over your house.   
> And to pass the butter.

A voice-driven AI engineering copilot powered by OpenClaw + Claude, built to run hands-free on the bike trainer.

---

## What it does

- **Status briefing** — today's calendar + open GitLab MRs, spoken concisely
- **PiAware aircraft tracking** — "anything interesting flying overhead?"
- **MR code review** — pulls diffs from GitLab, summarizes by voice
- **Comment posting** — posts GitLab review comments by voice command
- **Manager report** — runs the manager CLI, analyzes and speaks the output

## Architecture

The homelab miniPC is the gateway host — it owns all Claude API calls, skills, cron jobs, and API integrations, 
running 24/7. The MacBook Pro is a paired node that provides voice I/O (wake word detection, ElevenLabs TTS playback) 
and local macOS execution via `node.invoke → system.run`.

```
┌───────────────────────┐          ┌─────────────────────────────────┐
│   MacBook Pro         │          │   Homelab MiniPC (Ubuntu)       │
│   (Thin Client/Node)  │◄── LAN ─►│   (Gateway Host)                │
│                       │    WS    │                                 │
│  • Mic / Speaker      │          │  • ButterRobot server (:8585)   │
│  • Voice wake word    │          │  • OpenClaw Gateway (:18789)    │
│  • ElevenLabs TTS     │          │  • Claude API (Anthropic)       │
│  • macOS execution    │          │  • GitLab API                   │
│    (IntelliJ, git,    │          │  • PiAware feed (LAN poll)      │
│     manager CLI)      │          │  • Calendar API                 │
└───────────────────────┘          └─────────────────────────────────┘
```

## Tech Stack

| Tool                    | Purpose                              |
|-------------------------|--------------------------------------|
| FastAPI                 | Web framework                        |
| Pydantic                | Data validation                      |
| uv                      | Package and project management       |
| ty                      | Static type checking                 |
| ruff                    | Linting and formatting               |
| pytest + pytest-cov     | Testing and coverage                 |
| Docker + docker-compose | Containerized deployment (port 8585) |

## Running locally

```bash
# Install dependencies
uv sync

# Start the server
uv run fastapi dev app.py

# Or with Docker
docker compose up --build
```

Server runs at `http://localhost:8585`.

## Development

```bash
uv run task test_cov   # tests with coverage
uv run task lint       # lint
uv run task lint_fix   # auto-fix lint issues
uv run task format     # format
uv run task typecheck  # type check
```
