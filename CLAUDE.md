# ButterRobot — Claude Code Instructions

## Project Goal

ButterRobot is "Jarvis" — a voice-driven AI engineering copilot built for hands-free use on the bike trainer. It runs on a homelab miniPC (Ubuntu) and pairs with a MacBook Pro as a thin voice/display client over LAN WebSocket.

**Target capabilities (in order):**
1. Status briefing — calendar + open GitLab MRs
2. PiAware aircraft tracking ("anything interesting flying overhead?")
3. Voice-driven GitLab MR review and comment posting
4. Manager CLI integration (team reports, vacations)
5. macOS control — IntelliJ, terminal, git ops via MacBook node

## Architecture

The miniPC is the gateway host. It owns all Claude API calls, skills, cron jobs, and API integrations. It runs 24/7 independent of the MacBook. The MacBook is a paired node that provides voice I/O (wake word, TTS playback) and local macOS execution via `node.invoke → system.run`.

## Technology Choices

This is a uv-managed Python project.

| Tool | Purpose |
|------|---------|
| **FastAPI** | Web framework for the ButterRobot server |
| **Pydantic** | Data validation and serialization |
| **uv** | Package and project management (`pyproject.toml`) |
| **pytest** + **pytest-cov** | Testing and coverage |
| **ruff** | Linting and formatting |
| **ty** | Static type checking (Astral) |
| **Docker + docker-compose** | Container build and deployment, port 8585 |

## Common Commands

```bash
# Run tests with coverage
uv run task test_cov

# Lint
uv run task lint

# Auto-fix lint issues
uv run task lint_fix

# Format
uv run task format

# Type check
uv run task typecheck
```

## Conventions

- All endpoints must have return type annotations.
- Tests live in `tests/` and use `fastapi.testclient.TestClient`.
- Do not use `pyright` — this project uses `ty` for type checking.
- Do not include ticket numbers in code comments.
- Keep responses and briefings concise — the user may be on a bike trainer.
