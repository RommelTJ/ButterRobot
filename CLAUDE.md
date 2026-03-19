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

| Tool                        | Purpose                                                         |
|-----------------------------|-----------------------------------------------------------------|
| **FastAPI**                 | Web framework for the ButterRobot server                        |
| **uvicorn**                 | ASGI server (invoked directly for SSL support)                  |
| **websockets**              | WebSocket proxy to OpenClaw Gateway                             |
| **OpenClaw**                | AI agent runtime (Gateway on miniPC at `:18789`)                |
| **Pydantic**                | Data validation and serialization                               |
| **uv**                      | Package and project management (`pyproject.toml`)               |
| **pytest** + **pytest-cov** | Testing and coverage                                            |
| **ruff**                    | Linting and formatting                                          |
| **ty**                      | Static type checking (Astral)                                   |
| **Docker + docker-compose** | Container build and deployment, port 8585 (HTTPS)               |
| **mkcert**                  | Local TLS cert for HTTPS on LAN (cert at `~/.certs/` on miniPC) |

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

## Infrastructure

### miniPC (homelab, 192.168.0.205)
- OS: Ubuntu 24.04 LTS, PipeWire audio (with AirPlay/RAOP support)
- Hostname: `homelab.homelab.com` (add to `/etc/hosts` on any client: `192.168.0.205 homelab.homelab.com homelab`)
- OpenClaw gateway runs on `127.0.0.1:18789` (loopback only)
- ButterRobot runs in Docker at port 8585 (HTTPS), proxies to OpenClaw gateway
- PiAware poller runs as a systemd user service (on host, not Docker — needs `pw-play` for AirPlay)
- AirPlay sink: Office HomePod at `raop_sink.Office-HomePod.local.192.168.0.84.7000`
- mkcert CA at `~/.local/share/mkcert/rootCA.pem` — must be installed on each client machine:
  ```bash
  scp rommel@homelab.homelab.com:/home/rommel/.local/share/mkcert/rootCA.pem /tmp/homelab-rootCA.pem
  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain /tmp/homelab-rootCA.pem
  ```
- TLS cert at `~/.certs/cert.pem` covers: `homelab`, `homelab.homelab.com`, `192.168.0.205`, `localhost`, `127.0.0.1`
- Restart gateway: `openclaw gateway stop && openclaw gateway`
- Restart ButterRobot: `cd ~/ButterRobot && docker compose restart`

### OpenClaw config (`~/.openclaw/openclaw.json`)
- Gateway auth token: stored in `~/.openclaw/openclaw.json` on the miniPC — do not commit
- Allowed origins include `https://homelab:8585` and `https://homelab.homelab.com:8585`
- ElevenLabs voice: Callum (N2lVS1w4EtoT3dr4eOWO), configured in both `talk` and `messages.tts` sections

### MacBook (client node)
- OpenClaw macOS app connects to gateway via `wss://homelab.homelab.com:8585` (ButterRobot TLS proxy)
- WebChat dashboard: `https://homelab.homelab.com:8585`
- **Working audio setup for Talk Mode**: USB mic (Logitech MX Brio) as input + WH-1000XM5 via Bluetooth as output
  - Bluetooth headphones as input cause Bluetooth profile switching (A2DP→HFP) which silently breaks `SFSpeechRecognizer`
  - Wired headphones (3.5mm jack) work as both input and output
  - Never use a Bluetooth device as the macOS audio input for Talk Mode

### Voice Interaction
- **Talk Mode** (mic icon in macOS app): tap once to start a session → speak naturally → agent responds → ElevenLabs TTS plays through speakers automatically
- Talk Mode is the voice interaction method — wake word was abandoned

## Adding OpenClaw Skills

Skills are **Markdown files, not code**. They teach the OpenClaw agent what exec tool commands to run. No Python, no new dependencies.

### Process

1. **Create the skill** at `workspace/skills/<name>/SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: <skill-name>
   description: One-line description of what the skill does.
   metadata: {"openclaw":{"requires":{"env":["ENV_VAR_1","ENV_VAR_2"]}}}
   ---
   ```
2. **Add a reference** in `workspace/TOOLS.md` pointing to the skill
3. **Set env vars** on the miniPC — add `Environment=` lines to the systemd unit:
   ```
   ~/.config/systemd/user/openclaw-gateway.service
   ```
   Then reload and restart:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart openclaw-gateway.service
   ```
4. **Pull on the miniPC** — the workspace is symlinked (`~/.openclaw/workspace -> ~/ButterRobot/workspace`), so `git pull` is enough
5. **Test via WebChat** at `https://homelab.homelab.com:8585`

### Notes

- `openclaw skills list` checks the CLI's shell env, not the gateway's. A skill may show `✗ missing` in the CLI but work fine at runtime. Verify with: `cat /proc/$(systemctl --user show openclaw-gateway.service -p MainPID --value)/environ | tr '\0' '\n' | grep <VAR>`
- Project IDs and team members live in the gitlab skill as a reference — update them there when the team changes
- Credentials from Rommel's git remotes on the MacBook (under `~/code/work/chatmeter/`) can be used to find API tokens

### PiAware (Raspberry Pi, 192.168.0.211)
- Hostname: `piaware.homelab.com` (add to `/etc/hosts`: `192.168.0.211 piaware.homelab.com`)
- dump1090-fa (1090 MHz ADS-B): `http://piaware.homelab.com:8080/data/aircraft.json`
- skyaware978 (978 MHz UAT): `http://piaware.homelab.com:80/data/aircraft.json` (may 404 if UAT receiver not running)

### PiAware Poller (systemd service on miniPC)
- **Script**: `app/piaware_poller.py` — pure stdlib Python, runs directly on the host (not in Docker)
- **Service file**: `deploy/piaware-poller.service` — symlinked to `~/.config/systemd/user/piaware-poller.service`
- **Env file**: `~/.config/butterrobot/piaware-poller.env` (see `deploy/piaware-poller.env.example`)
- **Audio output**: ElevenLabs TTS API → mp3 → `pw-play` → PipeWire AirPlay → Office HomePod
- **State files**: `workspace/state/piaware-focus.json` (focus mode), `workspace/state/piaware-seen.json` (dedup)
- **Manage**:
  ```bash
  systemctl --user status piaware-poller.service
  systemctl --user restart piaware-poller.service
  journalctl --user -u piaware-poller.service -f   # tail logs
  ```
- **Env vars** (all in `piaware-poller.env`):
  - `PIAWARE_HOME_LAT`, `PIAWARE_HOME_LON` — home coordinates (required)
  - `PIAWARE_URL_1090`, `PIAWARE_URL_978` — feed endpoints
  - `PIAWARE_RADIUS_NM` (default 2), `PIAWARE_ALTITUDE_MAX` (default 5000), `PIAWARE_POLL_INTERVAL` (default 30)
  - `PIAWARE_STATE_DIR` — path to state files
  - `PIAWARE_AUDIO_SINK` — PipeWire AirPlay sink name (required for audio)
  - `ELEVENLABS_API_KEY` — ElevenLabs API key (required for audio)
  - `ELEVENLABS_VOICE_ID` — voice to use (default: Callum)
- **Gateway env vars** (in `~/.config/systemd/user/openclaw-gateway.service.d/piaware.conf`):
  - `PIAWARE_HOME_LAT`, `PIAWARE_HOME_LON`, `PIAWARE_URL_1090`, `PIAWARE_URL_978` — for the OpenClaw skill's on-demand queries
  - `ELEVENLABS_API_KEY`, `PIAWARE_AUDIO_SINK` — also here for shared access

## Conventions

- All endpoints must have return type annotations.
- Tests are colocated with source in `app/` and use `fastapi.testclient.TestClient`.
- Do not use `pyright` — this project uses `ty` for type checking.
- Do not include ticket numbers in code comments.
- Keep responses and briefings concise — the user may be on a bike trainer.
