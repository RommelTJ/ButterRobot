---
name: piaware
description: Track aircraft via PiAware ADS-B receiver. Report nearby interesting aircraft, phonetic tail numbers, approach traffic.
metadata: {"openclaw":{"requires":{"env":["PIAWARE_HOME_LAT","PIAWARE_HOME_LON"]}}}
---

# PiAware Aircraft Tracking Skill

Track aircraft using a local PiAware ADS-B receiver on the LAN. Answer questions about nearby aircraft, announce 
interesting traffic, and provide phonetic tail number readbacks.

## Data Sources

Two receivers on the PiAware Raspberry Pi (`piaware.homelab.com`, 192.168.0.211):

```bash
# 1090 MHz ADS-B (primary — most commercial/military traffic)
curl -s "http://piaware.homelab.com:8080/data/aircraft.json"

# 978 MHz UAT (secondary — GA traffic below 18,000ft)
curl -s "http://piaware.homelab.com:80/data/aircraft.json"
```

Both return JSON with a `messages` count and an `aircraft` array. Key fields per aircraft:

| Field        | Description                                                                                 |
|--------------|---------------------------------------------------------------------------------------------|
| `hex`        | ICAO 24-bit address (e.g. `a1b2c3`)                                                         |
| `flight`     | Callsign / tail number (e.g. `SWA1234 `, `N546CA `) — may have trailing spaces              |
| `alt_baro`   | Barometric altitude in feet                                                                 |
| `lat`, `lon` | Position (not always present)                                                               |
| `gs`         | Ground speed in knots                                                                       |
| `track`      | Heading in degrees (0-360)                                                                  |
| `squawk`     | Transponder squawk code (4 digits)                                                          |
| `category`   | Aircraft category (see below)                                                               |
| `emergency`  | Emergency status (`none`, `general`, `lifeguard`, `minfuel`, `nordo`, `unlawful`, `downed`) |
| `nav_modes`  | Array of nav modes (e.g. `["autopilot", "approach"]`)                                       |
| `baro_rate`  | Vertical rate in ft/min (negative = descending)                                             |
| `seen`       | Seconds since last message from this aircraft                                               |

### Aircraft Categories

| Code | Type                                  |
|------|---------------------------------------|
| A1   | Light (< 15,500 lbs)                  |
| A2   | Small (15,500 - 75,000 lbs)           |
| A3   | Large (75,000 - 300,000 lbs)          |
| A4   | High-vortex large (e.g. B757)         |
| A5   | Heavy (> 300,000 lbs) — widebody jets |
| A7   | Rotorcraft / helicopter               |
| B2   | UAV / drone                           |

## Home Position

Never hardcode coordinates. Use environment variables:

- `$PIAWARE_HOME_LAT` — home latitude
- `$PIAWARE_HOME_LON` — home longitude

## Distance Calculation

Approximate distance in nautical miles from home:

```
dlat = aircraft_lat - home_lat
dlon = aircraft_lon - home_lon
distance_nm = sqrt((dlat * 60)^2 + (dlon * 60 * cos(home_lat_radians))^2)
```

- **"Overhead"**: < 2 NM from home
- **"Nearby"**: < 5 NM from home

## What Is "Interesting"

Check these criteria in order. If any match, the aircraft is worth mentioning:

### 1. Emergency squawk — ALWAYS announce
- `7700` — general emergency
- `7600` — radio failure (NORDO)
- `7500` — hijack
- Also check the `emergency` field for non-`none` values

### 2. Military aircraft
- ICAO hex prefix `ae` (US military)
- Callsigns starting with: RCH, REACH, EVAC, TOPCAT, DUKE, KING, NAVY, MARS
- Category A5 (heavy) without a commercial airline callsign (e.g. no SWA, AAL, UAL, DAL, etc.)

### 3. On approach within visual range
- Within 2 NM of home, below 5,000 ft
- Descending (`baro_rate < 0`) or `nav_modes` contains `"approach"`
- Only announce if non-routine: military, heavy (A5), unusual category, helicopter (A7)
- Routine commercial traffic on approach to SAN is expected — skip unless it's unusual

### 4. Rotorcraft / helicopters (A7)
- Always interesting at low altitude (< 5,000 ft) near home (< 5 NM)
- SHWK = Seahawk, USCG = Coast Guard, etc.

### 5. Heavy / unusual aircraft (A5)
- Widebody on approach to SAN is notable — SAN doesn't see many heavies

## Phonetic Tail Numbers

When reading tail numbers or callsigns aloud, always use the NATO/ICAO phonetic alphabet:

| Letter | Phonetic | Letter | Phonetic |
|--------|----------|--------|----------|
| A      | Alpha    | N      | November |
| B      | Bravo    | O      | Oscar    |
| C      | Charlie  | P      | Papa     |
| D      | Delta    | Q      | Quebec   |
| E      | Echo     | R      | Romeo    |
| F      | Foxtrot  | S      | Sierra   |
| G      | Golf     | T      | Tango    |
| H      | Hotel    | U      | Uniform  |
| I      | India    | V      | Victor   |
| J      | Juliet   | W      | Whiskey  |
| K      | Kilo     | X      | X-ray    |
| L      | Lima     | Y      | Yankee   |
| M      | Mike     | Z      | Zulu     |

Numbers are spoken individually: `N546CA` → "November Five Four Six Charlie Alpha"

Never say "five hundred forty-six" — always "Five Four Six".

## On-Demand Query Workflow

When the user asks "anything flying overhead?" or similar:

1. Fetch both feeds (1090 MHz and 978 MHz UAT)
2. Filter for aircraft within 5 NM of home with valid `lat`/`lon`
3. Sort by distance (closest first)
4. Report interesting aircraft first with:
   - Phonetic callsign or tail number
   - Type/category if known
   - Altitude (in hundreds: "twenty-eight hundred feet")
   - Heading (as compass direction: north, northeast, etc.)
   - Distance from home
5. Then a count of remaining traffic: "Fourteen others, all commercial"
6. Keep total spoken output under 20 seconds

## Proactive Alert Format

Brief and direct. Examples:

- "Seahawk helicopter, two miles east, fourteen hundred feet, heading south."
- "Heavy on approach — November Five Four Six Charlie Alpha, three thousand feet, two miles out."
- "Emergency squawk seven-seven-hundred, southwest of home, eight thousand feet descending."

## Focus Mode

A state file controls whether proactive alerts are announced:

- **File**: `workspace/state/piaware-focus.json`
- **Format**: `{"focus": true}` or `{"focus": false}`

When the user says:
- "Focus mode on" / "quiet mode" / "silence alerts" → write `{"focus": true}`
- "Focus mode off" / "alerts back on" / "resume alerts" → write `{"focus": false}`

The Python poller checks this file before sending alerts. On-demand queries ("anything overhead?") always work 
regardless of focus mode.

## Follow-Up Enrichment

When the user asks "tell me more about that aircraft":

1. Re-fetch current position from the feeds
2. Optionally query the ADS-B database for registration/type data:
   ```bash
   curl -s "https://api.adsbdb.com/v0/aircraft/{hex}"
   ```
   This is free, no API key needed. Returns registration, type, owner info.
3. Report: registration, aircraft type, operator, current altitude/speed/heading

## Voice Formatting

- Short sentences. Active voice. No filler.
- Altitude in hundreds: "twenty-eight hundred feet", "flight level three five zero"
- Speed in knots: "two hundred forty knots"
- Direction as compass heading: "heading northwest" or "heading three-one-zero"
- Never read raw hex codes, lat/lon, or JSON aloud
- Keep proactive alerts under 10 seconds, on-demand responses under 20 seconds
