# ButterRobot

**v0.6.1 — March 19, 2026**

> What is my purpose? To read your calendar, review your GitLab MRs, and tell you what's flying over your house.   
> And to pass the butter.

A voice-driven AI engineering copilot powered by OpenClaw + Claude, built to run hands-free on the bike trainer.

---

## What it does

- **Status briefing** — today's calendar + open GitLab MRs, spoken concisely
- **PiAware aircraft tracking** — "anything interesting flying overhead?"
- **MR code review** — pulls diffs from GitLab, summarizes by voice
- **Comment posting** — posts GitLab review comments by voice command

## Architecture

The homelab miniPC is the gateway host — it owns all Claude API calls, skills, cron jobs, and API integrations,
running 24/7. The MacBook Pro is a paired node that provides voice I/O (Talk Mode, ElevenLabs TTS playback)
and WebChat access.

```
┌───────────────────────┐          ┌─────────────────────────────────┐
│   MacBook Pro         │          │   Homelab MiniPC (Ubuntu)       │
│   (Thin Client/Node)  │◄── LAN ─►│   (Gateway Host)                │
│                       │    WS    │                                 │
│  • Mic / Speaker      │          │  • ButterRobot server (:8585)   │
│  • Voice wake word    │          │  • OpenClaw Gateway (:18789)    │
│  • ElevenLabs TTS     │          │  • Claude API (Anthropic)       │
│  • Talk Mode (voice)  │          │  • GitLab API                   │
│  • WebChat dashboard  │          │  • PiAware feed (LAN poll)      │
│                       │          │  • Calendar (ICS feed)          │
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

## PiAware Aircraft Tracking

ButterRobot includes a PiAware skill and a Python poller for aircraft tracking via ADS-B.

**Skill** (`workspace/skills/piaware/SKILL.md`): Teaches the OpenClaw agent to interpret aircraft data, respond to on-demand queries ("anything flying overhead?"), and speak phonetic tail numbers.

**Poller** (`app/piaware_poller.py`): A standalone Python script (pure stdlib, no pip dependencies) that runs as a systemd user service on the miniPC host. Polls the 1090 MHz feed every 30 seconds, filters for aircraft within range, synthesizes speech via ElevenLabs TTS, and plays alerts on the Office HomePod via PipeWire AirPlay.

### How It Works

```
PiAware (RPi) → HTTP JSON → Poller (miniPC) → ElevenLabs TTS → pw-play → AirPlay → Office HomePod
```

The poller runs on the host (not Docker) because it needs `pw-play` access to the PipeWire audio system for AirPlay output.

### Environment Variables

All configured in `~/.config/butterrobot/piaware-poller.env` on the miniPC. See `deploy/piaware-poller.env.example`.

| Variable                | Default                                              | Description                           |
|-------------------------|------------------------------------------------------|---------------------------------------|
| `PIAWARE_HOME_LAT`      | (required)                                           | Home latitude                         |
| `PIAWARE_HOME_LON`      | (required)                                           | Home longitude                        |
| `ELEVENLABS_API_KEY`    | (required)                                           | ElevenLabs API key for TTS            |
| `PIAWARE_AUDIO_SINK`    | (required)                                           | PipeWire AirPlay sink name            |
| `ELEVENLABS_VOICE_ID`   | `weA4Q36twV5kwSaTEL0Q`                               | ElevenLabs voice (Callum)             |
| `PIAWARE_URL_1090`      | `http://piaware.homelab.com:8080/data/aircraft.json` | dump1090-fa endpoint                  |
| `PIAWARE_URL_978`       | `http://piaware.homelab.com:80/data/aircraft.json`   | skyaware978 UAT endpoint              |
| `PIAWARE_RADIUS_NM`     | `2`                                                  | Alert radius in nautical miles        |
| `PIAWARE_ALTITUDE_MAX`  | `5000`                                               | Max altitude in feet to consider      |
| `PIAWARE_POLL_INTERVAL` | `30`                                                 | Seconds between polls                 |
| `PIAWARE_STATE_DIR`     | `workspace/state`                                    | State directory for focus/dedup files |

### Deployment

```bash
# Service file is symlinked from the repo
ln -sf ~/ButterRobot/deploy/piaware-poller.service ~/.config/systemd/user/piaware-poller.service
systemctl --user daemon-reload
systemctl --user enable --now piaware-poller.service

# Check status / logs
systemctl --user status piaware-poller.service
journalctl --user -u piaware-poller.service -f
```

### Focus Mode

Toggle via voice ("focus mode on" / "focus mode off") to silence proactive alerts. On-demand queries always work regardless.

## Calendar Integration

Office365/Outlook calendar integration via a published ICS feed. No OAuth, no Azure app registration — just a URL. Fetches events for status briefings and on-demand queries ("What's on my calendar?", "Anything tomorrow?").

**Skill** (`workspace/skills/calendar/SKILL.md`): Teaches the OpenClaw agent to invoke the helper and summarize events concisely for voice.

**Helper** (`app/calendar_helper.py`): Fetches the ICS feed, filters by date, handles recurring events, outputs JSON to stdout.

### Setup

1. Outlook web → Settings → Calendar → Shared calendars → Publish a calendar → copy the ICS link
2. Set `CALENDAR_ICS_URL` in the gateway systemd environment on the miniPC

See `deploy/calendar-helper.env.example`.

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
