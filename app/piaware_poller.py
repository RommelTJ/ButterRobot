"""PiAware aircraft poller — monitors ADS-B feeds for interesting aircraft."""

import json
import logging
import math
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

EMERGENCY_SQUAWKS = {"7700", "7600", "7500"}
MILITARY_HEX_PREFIXES = ("ae",)
MILITARY_CALLSIGN_PREFIXES = (
    "RCH",
    "REACH",
    "EVAC",
    "TOPCAT",
    "DUKE",
    "KING",
    "NAVY",
    "MARS",
)
COMMERCIAL_PREFIXES = (
    "SWA",
    "AAL",
    "UAL",
    "DAL",
    "ASA",
    "JBU",
    "NKS",
    "FFT",
    "SKW",
    "RPA",
    "ENY",
    "PDT",
    "AWI",
    "BAW",
    "AFR",
    "DLH",
    "ANA",
    "JAL",
    "KAL",
    "CPA",
    "QFA",
    "UAE",
    "FDX",
    "UPS",
)
INTERESTING_CATEGORIES = {"A5", "A7", "B2"}

COMPASS_DIRECTIONS = [
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
]


def calculate_distance_nm(
    home_lat: float, home_lon: float, ac_lat: float, ac_lon: float
) -> float:
    """Approximate distance in nautical miles using flat-earth formula."""
    dlat = ac_lat - home_lat
    dlon = ac_lon - home_lon
    cos_lat = math.cos(math.radians(home_lat))
    return math.sqrt((dlat * 60) ** 2 + (dlon * 60 * cos_lat) ** 2)


def is_emergency_squawk(aircraft: dict) -> bool:
    """Check if an aircraft has an emergency squawk code or emergency status."""
    squawk = aircraft.get("squawk", "")
    if squawk in EMERGENCY_SQUAWKS:
        return True
    emergency = aircraft.get("emergency", "none")
    return emergency not in ("none", "", None)


def is_military(aircraft: dict) -> bool:
    """Check if an aircraft appears to be military."""
    hex_code = aircraft.get("hex", "").lower()
    if any(hex_code.startswith(p) for p in MILITARY_HEX_PREFIXES):
        return True
    callsign = aircraft.get("flight", "").strip().upper()
    if callsign and any(callsign.startswith(p) for p in MILITARY_CALLSIGN_PREFIXES):
        return True
    return False


def track_to_compass(track: float | None) -> str:
    """Convert a track heading (0-360) to a compass direction string."""
    if track is None:
        return "unknown"
    index = round(track / 45) % 8
    return COMPASS_DIRECTIONS[index]


class AircraftFilter:
    """Filters aircraft for interesting traffic near home."""

    def __init__(
        self,
        home_lat: float,
        home_lon: float,
        radius_nm: float = 2.0,
        altitude_max: int = 5000,
    ):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.radius_nm = radius_nm
        self.altitude_max = altitude_max

    def is_interesting(self, aircraft: dict) -> bool:
        """Determine if an aircraft is interesting enough to announce."""
        # Emergency squawks are always interesting, regardless of position
        if is_emergency_squawk(aircraft):
            return True

        # Need position for all other checks
        lat = aircraft.get("lat")
        lon = aircraft.get("lon")
        if lat is None or lon is None:
            return False

        distance = calculate_distance_nm(self.home_lat, self.home_lon, lat, lon)
        alt = aircraft.get("alt_baro")

        # Must be within altitude ceiling (if we have altitude data)
        if alt is not None and alt > self.altitude_max:
            return False

        # Military aircraft within range
        if is_military(aircraft) and distance <= self.radius_nm:
            return True

        # Helicopter / rotorcraft at low altitude nearby (wider 5nm radius)
        category = aircraft.get("category", "")
        if category == "A7" and distance <= max(self.radius_nm, 5.0):
            return True

        # Heavy aircraft on approach
        if category == "A5" and distance <= self.radius_nm:
            callsign = aircraft.get("flight", "").strip().upper()
            # Only interesting if not routine commercial
            is_commercial = any(
                callsign.startswith(p) for p in COMMERCIAL_PREFIXES
            )
            if not is_commercial:
                return True
            # Commercial heavy on approach to SAN is still notable
            baro_rate = aircraft.get("baro_rate", 0)
            nav_modes = aircraft.get("nav_modes", [])
            if baro_rate is not None and baro_rate < 0:
                return True
            if isinstance(nav_modes, list) and "approach" in nav_modes:
                return True

        return False

    def filter_interesting(self, aircraft_list: list[dict]) -> list[dict]:
        """Filter a list of aircraft to only interesting ones."""
        return [ac for ac in aircraft_list if self.is_interesting(ac)]


class PiawarePoller:
    """Polls PiAware feeds and tracks state for dedup and focus mode."""

    def __init__(
        self,
        home_lat: float,
        home_lon: float,
        radius_nm: float,
        altitude_max: int,
        poll_interval: int,
        url_1090: str,
        url_978: str,
        state_dir: Path,
    ):
        self.filter = AircraftFilter(
            home_lat=home_lat,
            home_lon=home_lon,
            radius_nm=radius_nm,
            altitude_max=altitude_max,
        )
        self.poll_interval = poll_interval
        self.url_1090 = url_1090
        self.url_978 = url_978
        self.state_dir = state_dir
        self._seen: dict[str, float] = {}
        self._focus: bool = False

    def fetch_feed(self, url: str) -> list[dict]:
        """Fetch aircraft list from a PiAware JSON endpoint."""
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read())
                return data.get("aircraft", [])
        except Exception:
            logger.debug("Failed to fetch feed from %s", url, exc_info=True)
            return []

    def merge_feeds(
        self, feed_1090: list[dict], feed_978: list[dict]
    ) -> list[dict]:
        """Merge two aircraft feeds, deduplicating by hex. Prefer lower 'seen' value."""
        by_hex: dict[str, dict] = {}
        for ac in feed_1090:
            hex_code = ac.get("hex", "")
            if hex_code:
                by_hex[hex_code] = ac
        for ac in feed_978:
            hex_code = ac.get("hex", "")
            if hex_code:
                existing = by_hex.get(hex_code)
                if existing is None or ac.get("seen", 999) < existing.get(
                    "seen", 999
                ):
                    by_hex[hex_code] = ac
        return list(by_hex.values())

    def is_new(self, aircraft: dict, ttl_seconds: int = 900) -> bool:
        """Check if an aircraft hasn't been announced recently."""
        hex_code = aircraft.get("hex", "")
        last_seen = self._seen.get(hex_code)
        if last_seen is None:
            return True
        return (time.time() - last_seen) > ttl_seconds

    def mark_seen(self, hex_code: str) -> None:
        """Mark an aircraft as recently announced."""
        self._seen[hex_code] = time.time()

    def prune_seen(self, ttl_seconds: int = 900) -> None:
        """Remove entries older than TTL from the seen map."""
        now = time.time()
        self._seen = {
            k: v for k, v in self._seen.items() if (now - v) <= ttl_seconds
        }

    def is_focus_mode(self) -> bool:
        """Check if focus mode is currently active."""
        return self._focus

    def load_focus_state(self) -> None:
        """Load focus mode state from disk."""
        focus_file = self.state_dir / "piaware-focus.json"
        try:
            data = json.loads(focus_file.read_text())
            self._focus = data.get("focus", False)
        except (FileNotFoundError, json.JSONDecodeError):
            self._focus = False

    def save_seen_state(self) -> None:
        """Persist the seen map to disk."""
        seen_file = self.state_dir / "piaware-seen.json"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        seen_file.write_text(json.dumps(self._seen))

    def load_seen_state(self) -> None:
        """Load the seen map from disk."""
        seen_file = self.state_dir / "piaware-seen.json"
        try:
            self._seen = json.loads(seen_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            self._seen = {}

    def poll_once(self) -> list[dict]:
        """Run one poll cycle. Returns list of new interesting aircraft to announce."""
        self.load_focus_state()
        if self.is_focus_mode():
            return []

        feed_1090 = self.fetch_feed(self.url_1090)
        feed_978 = self.fetch_feed(self.url_978)
        merged = self.merge_feeds(feed_1090, feed_978)
        interesting = self.filter.filter_interesting(merged)

        new_alerts = []
        for ac in interesting:
            if self.is_new(ac):
                new_alerts.append(ac)
                self.mark_seen(ac.get("hex", ""))

        self.prune_seen()
        self.save_seen_state()
        return new_alerts

    def speak_alert(self, text: str) -> bool:
        """Synthesize speech via ElevenLabs and play on the AirPlay sink."""
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        voice_id = os.environ.get(
            "ELEVENLABS_VOICE_ID", "weA4Q36twV5kwSaTEL0Q"
        )
        sink = os.environ.get("PIAWARE_AUDIO_SINK", "")

        if not api_key:
            logger.error("ELEVENLABS_API_KEY not set, cannot speak alert")
            return False
        if not sink:
            logger.error("PIAWARE_AUDIO_SINK not set, cannot play audio")
            return False

        try:
            audio_data = self._elevenlabs_tts(text, api_key, voice_id)
            if not audio_data:
                return False
            return self._play_audio(audio_data, sink)
        except Exception:
            logger.exception("Failed to speak alert")
            return False

    def _elevenlabs_tts(
        self, text: str, api_key: str, voice_id: str
    ) -> bytes | None:
        """Call ElevenLabs TTS API and return audio bytes."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        payload = json.dumps({
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        except Exception:
            logger.exception("ElevenLabs TTS request failed")
            return None

    def _play_audio(self, audio_data: bytes, sink: str) -> bool:
        """Write audio to a temp file and play via pw-play to the AirPlay sink."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["pw-play", f"--target={sink}", tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    "pw-play failed (rc=%d): %s",
                    result.returncode,
                    result.stderr.strip(),
                )
                return False
            return True
        except FileNotFoundError:
            logger.error("pw-play not found in PATH")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("pw-play timed out")
            return False
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def format_alert(self, aircraft: dict) -> str:
        """Format an aircraft dict into a spoken alert sentence."""
        callsign = aircraft.get("flight", "").strip()
        alt = aircraft.get("alt_baro")
        heading = track_to_compass(aircraft.get("track"))
        category = aircraft.get("category", "")
        hex_code = aircraft.get("hex", "")

        lat = aircraft.get("lat")
        lon = aircraft.get("lon")
        if lat is not None and lon is not None:
            distance = calculate_distance_nm(
                self.filter.home_lat, self.filter.home_lon, lat, lon
            )
            dist_str = f"{distance:.0f} mile{'s' if distance >= 1.5 else ''} out"
        else:
            dist_str = "nearby"

        # Build type description
        parts = []
        if is_emergency_squawk(aircraft):
            squawk = aircraft.get("squawk", "")
            parts.append(f"Emergency squawk {squawk}")
        if is_military(aircraft):
            parts.append("Military")
        if category == "A7":
            parts.append("helicopter")
        elif category == "A5":
            parts.append("heavy")
        elif not parts:
            parts.append("Aircraft")

        type_str = " ".join(parts)

        # Format altitude in spoken style
        if alt is not None and isinstance(alt, (int, float)):
            alt_hundreds = round(alt / 100) * 100
            alt_str = f"{alt_hundreds} feet"
        else:
            alt_str = "altitude unknown"

        # Identify the aircraft
        ident = callsign or hex_code or "no callsign"

        return f"{type_str}, {ident}, {dist_str}, {alt_str}, heading {heading}."


def main() -> None:
    """Entry point for the PiAware poller daemon."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    home_lat = float(os.environ["PIAWARE_HOME_LAT"])
    home_lon = float(os.environ["PIAWARE_HOME_LON"])
    radius_nm = float(os.environ.get("PIAWARE_RADIUS_NM", "2"))
    altitude_max = int(os.environ.get("PIAWARE_ALTITUDE_MAX", "5000"))
    poll_interval = int(os.environ.get("PIAWARE_POLL_INTERVAL", "30"))
    url_1090 = os.environ.get(
        "PIAWARE_URL_1090",
        "http://piaware.homelab.com:8080/data/aircraft.json",
    )
    url_978 = os.environ.get(
        "PIAWARE_URL_978",
        "http://piaware.homelab.com:80/data/aircraft.json",
    )

    # Default state dir: workspace/state/ relative to project root
    state_dir = Path(
        os.environ.get("PIAWARE_STATE_DIR", "workspace/state")
    )

    poller = PiawarePoller(
        home_lat=home_lat,
        home_lon=home_lon,
        radius_nm=radius_nm,
        altitude_max=altitude_max,
        poll_interval=poll_interval,
        url_1090=url_1090,
        url_978=url_978,
        state_dir=state_dir,
    )

    logger.info(
        "PiAware poller started — home=(%.4f, %.4f), radius=%.1f NM, "
        "altitude_max=%d ft, poll every %ds",
        home_lat,
        home_lon,
        radius_nm,
        altitude_max,
        poll_interval,
    )

    while True:
        try:
            alerts = poller.poll_once()
            for ac in alerts:
                message = poller.format_alert(ac)
                logger.info("Alert: %s", message)
                poller.speak_alert(message)
        except Exception:
            logger.exception("Error during poll cycle")
        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
