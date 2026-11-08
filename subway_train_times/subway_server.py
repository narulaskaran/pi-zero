#!/usr/bin/env python3
"""
Home Edit - shared-home weather and reminder board
"""

import io
import hashlib
import os
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml
import requests
from flask import Flask, send_file, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import home_edit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

try:
    from presence_detector import PresenceDetector
except ImportError:
    PresenceDetector = None

try:
    from shared_presence_state import SharedPresenceState
except ImportError:
    SharedPresenceState = None

try:
    import overlay_store
except ImportError:
    overlay_store = None

app = Flask(__name__)

# ============ CONFIG ============
# Global presence detector (initialized on first use)
# Note: Presence detection is now handled by Waveshare display (every 45s)
# and shared via file. This detector is only used as fallback.
_presence_detector = None
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
TRANSIT_TRAIN_COUNT = 4
SIDEBAR_X = 560

SCRIPT_DIR = Path(__file__).parent.resolve()
LOCAL_FONT_TEXT = SCRIPT_DIR / "Roboto-Bold.ttf"
LOCAL_FONT_ICON = SCRIPT_DIR / "DejaVuSans.ttf"

SYSTEM_ICON_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "arial.ttf"]

# COLORS
COLOR_WHITE = 255
COLOR_BLACK = 0
COLOR_GRAY = 80


def get_font(size, is_bold=False, is_icon=False):
    font_path = None
    if is_icon:
        if LOCAL_FONT_ICON.exists():
            font_path = str(LOCAL_FONT_ICON)
    else:
        if LOCAL_FONT_TEXT.exists():
            font_path = str(LOCAL_FONT_TEXT)
        elif LOCAL_FONT_ICON.exists():
            font_path = str(LOCAL_FONT_ICON)

    if not font_path:
        for path in SYSTEM_ICON_PATHS:
            if os.path.exists(path):
                font_path = path
                break

    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except:
            pass
    return ImageFont.load_default()


def load_config():
    try:
        with open(SCRIPT_DIR / "config.yaml", "r") as f:
            return yaml.safe_load(f)
    except:
        return {}


def get_presence_detector():
    """Get or initialize the global presence detector."""
    global _presence_detector
    if _presence_detector is None and PresenceDetector is not None:
        config = load_config()
        refresh_config = config.get("refresh_rate", {})
        devices = refresh_config.get("devices", [])
        if devices:
            # Initialize with 10-minute grace period (600 seconds)
            _presence_detector = PresenceDetector(
                mac_addresses=devices,
                cache_duration=30,
                grace_period_seconds=600
            )
            logger.info(f"Initialized presence detector with {len(devices)} devices and 10-minute grace period")
    return _presence_detector




def calculate_refresh_rate():
    """Fixed shared-home refresh interval, including away/night states."""
    return 900


# ============ DATA ============
def get_weather(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "apparent_temperature", "weather_code"],
            "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_probability_max", "sunrise", "sunset"],
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "forecast_days": 8,
        }
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return None


# ============ DRAWING HELPERS ============
_air_cache = {}
_air_lock = threading.Lock()


def get_air_quality(lat, lon):
    """Modeled US AQI. Cache for 15 minutes; never label an old failed reading current."""
    key = (lat, lon)
    with _air_lock:
        now = time.monotonic()
        item = _air_cache.get(key)
        if item and now - item[0] < item[2]:
            return item[1]
        try:
            response = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality",
                                    params={"latitude": lat, "longitude": lon, "current": "us_aqi"}, timeout=5)
            response.raise_for_status()
            value = response.json().get("current", {}).get("us_aqi")
            _air_cache[key] = (now, value, 900)
            return value
        except (requests.RequestException, OSError, ValueError):
            _air_cache[key] = (now, None, 60)
            return None


def draw_overlay(img, draw, overlay):
    """Editorial overlay treatment; store/expiry/priority behavior remains unchanged."""
    image_path = overlay_store.get_image(overlay["id"]) if overlay.get("has_image") else None
    home_edit.draw_overlay(img, overlay, image_path)


def apply_overlays(img, draw):
    """Draw the highest-priority active overlay of each slot.

    A fullscreen overlay covers the body, so sidebar/banner are skipped
    while one is active.
    """
    if overlay_store is None:
        return
    try:
        fullscreen = overlay_store.active("fullscreen")
        if fullscreen:
            draw_overlay(img, draw, fullscreen[0])
            return
        for slot in ("sidebar", "banner"):
            candidates = overlay_store.active(slot)
            if candidates:
                draw_overlay(img, draw, candidates[0])
    except Exception as e:
        # Overlays must never break the core dashboard.
        logger.error(f"Overlay rendering failed, showing base dashboard: {e}")


def generate_image(battery_percent=None, now=None, weather=None, subway=None, refresh_seconds=None):
    """Render Home Edit; legacy injection arguments are accepted without transit fetches."""
    now = now or datetime.now()
    config = load_config()
    station = (config.get("stations") or config.get("stops") or [{}])[0]
    lat, lon = station.get("lat", 40.78), station.get("lon", -73.97)
    if weather is None:
        weather = get_weather(lat, lon)
    aqi = get_air_quality(lat, lon)
    sidebar = bool(overlay_store and overlay_store.active("sidebar"))
    img = home_edit.render(now, weather, aqi, battery_percent, has_sidebar=sidebar)
    apply_overlays(img, ImageDraw.Draw(img))
    return img


@app.route("/refresh-rate")
def get_refresh_rate():
    """Return the current refresh rate in minutes as JSON.

    The Arduino firmware expects {"refresh_minutes": N} where N is the
    number of minutes to sleep between display updates. The internal
    calculate_refresh_rate() returns seconds, so we convert here.
    """
    try:
        refresh_seconds = calculate_refresh_rate()
        refresh_minutes = max(1, refresh_seconds // 60)
        logger.debug(f"Returning refresh_minutes={refresh_minutes} to Arduino")
        return jsonify({"refresh_minutes": refresh_minutes})
    except Exception as e:
        # On error, return a safe default (2 minutes)
        logger.error(f"Error in get_refresh_rate: {e}")
        return jsonify({"refresh_minutes": 2, "error": str(e)}), 500


@app.route("/status")
def get_status():
    """Debug endpoint showing current presence detection state."""
    try:
        config = load_config()
        refresh_config = config.get("refresh_rate", {})

        status = {
            "timestamp": datetime.now().isoformat(),
            "architecture": "shared_state_file",
            "note": "Presence detection handled by Waveshare display (every 45s)",
            "overlay_api": overlay_store is not None,
            "layout": "home_edit",
            "renderer_version": "home-edit-1",
            "renderer_sha256": hashlib.sha256(Path(home_edit.__file__).read_bytes()).hexdigest(),
            "active_overlays": len(overlay_store.active()) if overlay_store else 0,
        }

        # Get shared state info
        if SharedPresenceState is not None:
            shared_state_info = SharedPresenceState.get_state_info()
            status["shared_state"] = shared_state_info

            # Get current presence from shared state
            is_home, timestamp, is_stale = SharedPresenceState.read_state()
            if is_home is not None:
                status["is_home"] = is_home
                status["is_home_source"] = "shared_state" if not is_stale else "shared_state_stale"
        else:
            status["shared_state"] = {"error": "SharedPresenceState module not available"}

        # Get refresh rate info
        refresh_seconds = calculate_refresh_rate()
        status["current_refresh_seconds"] = refresh_seconds
        status["current_refresh_minutes"] = refresh_seconds // 60

        intervals = refresh_config.get("intervals", {})
        status["configured_intervals"] = {"fast": 900, "slow": 900, "night": 900}

        return jsonify(status)
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/overlays", methods=["GET"])
def list_overlays():
    """List unexpired overlays. ?active=1 filters to currently-rendering ones."""
    if overlay_store is None:
        return jsonify({"error": "overlay_store module not available"}), 500
    if request.args.get("active"):
        return jsonify({"overlays": overlay_store.active()})
    return jsonify({"overlays": overlay_store.list_all()})


@app.route("/overlay", methods=["POST"])
def create_overlay():
    """Push an overlay card to the display.

    JSON body:
      slot: "banner" (footer strip) | "sidebar" (right column) |
            "fullscreen" (whole body, header stays) — default "banner"
      title: short heading (optional)
      text: body text, word-wrapped (optional)
      image_b64: base64 PNG/JPEG, rendered dithered 1-bit (optional)
      ttl_seconds: lifetime, default 3600, capped at 7 days
      expires_at / starts_at: ISO timestamps (alternative to ttl)
      priority: int, higher wins when a slot has multiple overlays
      id: optional stable id — re-posting the same id replaces the overlay

    At least one of title/text/image_b64 is required. The e-ink display
    picks the change up on its next scheduled 15-minute poll.
    """
    if overlay_store is None:
        return jsonify({"error": "overlay_store module not available"}), 500
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "body must be valid JSON"}), 400
    try:
        overlay = overlay_store.add(payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    logger.info(f"Overlay added: {overlay['id']} slot={overlay['slot']} expires={overlay['expires_at']}")
    return jsonify(overlay), 201


@app.route("/overlay/<overlay_id>", methods=["DELETE"])
def delete_overlay(overlay_id):
    if overlay_store is None:
        return jsonify({"error": "overlay_store module not available"}), 500
    if overlay_store.remove(overlay_id):
        logger.info(f"Overlay removed: {overlay_id}")
        return jsonify({"deleted": overlay_id})
    return jsonify({"error": "not found"}), 404


@app.route("/overlays", methods=["DELETE"])
def clear_overlays():
    if overlay_store is None:
        return jsonify({"error": "overlay_store module not available"}), 500
    n = overlay_store.clear()
    logger.info(f"Overlays cleared: {n}")
    return jsonify({"cleared": n})


@app.route("/display.bmp")
def serve_bmp():
    # Get optional battery parameter (0-100)
    battery_param = request.args.get("battery", type=int)

    # Validate battery parameter
    if battery_param is not None:
        if not (0 <= battery_param <= 100):
            battery_param = None  # Invalid value, ignore it

    img = generate_image(battery_percent=battery_param)

    # === CRITICAL FIX ===
    # Convert to 1-bit B&W using dithering.
    # This solves the 385KB size issue and makes it ~48KB
    img = img.convert("1")
    # ====================

    b = io.BytesIO()
    img.save(b, "BMP")
    b.seek(0)
    return send_file(b, mimetype="image/bmp")


@app.route("/display.png")
def serve_png():
    img = generate_image()
    # Optional: convert PNG to 1-bit too if you want to preview the exact look
    # img = img.convert("1")
    b = io.BytesIO()
    img.save(b, "PNG")
    b.seek(0)
    return send_file(b, mimetype="image/png")


if __name__ == "__main__":
    # Load server config from config.yaml
    config = load_config()
    server_config = config.get("server", {})
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 5000)

    logger.info("Presence detection handled by Waveshare display (shared state file)")
    logger.info(f"Starting Flask server on {host}:{port}")
    app.run(host=host, port=port)
