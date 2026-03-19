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
| **uvicorn** | ASGI server (invoked directly for SSL support) |
| **websockets** | WebSocket proxy to OpenClaw Gateway |
| **OpenClaw** | AI agent runtime (Gateway on miniPC at `:18789`) |
| **Pydantic** | Data validation and serialization |
| **uv** | Package and project management (`pyproject.toml`) |
| **pytest** + **pytest-cov** | Testing and coverage |
| **ruff** | Linting and formatting |
| **ty** | Static type checking (Astral) |
| **Docker + docker-compose** | Container build and deployment, port 8585 (HTTPS) |
| **mkcert** | Local TLS cert for HTTPS on LAN (cert at `~/.certs/` on miniPC) |

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
- Hostname: `homelab.homelab.com` (add to `/etc/hosts` on any client: `192.168.0.205 homelab.homelab.com homelab`)
- OpenClaw gateway runs on `127.0.0.1:18789` (loopback only)
- ButterRobot runs in Docker at port 8585 (HTTPS), proxies to OpenClaw gateway
- mkcert CA at `~/.local/share/mkcert/rootCA.pem` — must be installed on each client machine:
  ```bash
  scp rommel@homelab.homelab.com:/home/rommel/.local/share/mkcert/rootCA.pem /tmp/homelab-rootCA.pem
  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain /tmp/homelab-rootCA.pem
  ```
- TLS cert at `~/.certs/cert.pem` covers: `homelab`, `homelab.homelab.com`, `192.168.0.205`, `localhost`, `127.0.0.1`
- Restart gateway: `openclaw gateway stop && openclaw gateway`
- Restart ButterRobot: `cd ~/ButterRobot && docker compose restart`

### OpenClaw config (`~/.openclaw/openclaw.json`)
- Gateway auth token: `6dcc826622553bff16131d9e1877e61a94c3a1172e5aa992`
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

## Conventions

- All endpoints must have return type annotations.
- Tests are colocated with source in `app/` and use `fastapi.testclient.TestClient`.
- Do not use `pyright` — this project uses `ty` for type checking.
- Do not include ticket numbers in code comments.
- Keep responses and briefings concise — the user may be on a bike trainer.
