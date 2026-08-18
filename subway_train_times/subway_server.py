#!/usr/bin/env python3
"""
Subway Dashboard - 1-Bit Dithered Fix
"""

import io
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
from nyct_gtfs import NYCTFeed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

try:
    from get_train_times import ROUTE_TO_FEED
except ImportError:
    ROUTE_TO_FEED = {}

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
    """
    Calculate the appropriate refresh rate in seconds based on:
    - Time of day (night mode)
    - Device presence (someone home)

    FAIL-OPEN BEHAVIOR: If presence detection fails, defaults to fast_rate
    to ensure fresh data when user is actually home.

    Returns:
        int: Refresh interval in seconds
    """
    config = load_config()
    refresh_config = config.get("refresh_rate", {})

    # Get configured intervals (with defaults)
    intervals = refresh_config.get("intervals", {})
    fast_rate = intervals.get("fast", 1)  # 1 second default
    slow_rate = intervals.get("slow", 30)  # 30 seconds default
    night_rate = intervals.get("night", 30)  # 30 seconds default

    # Get night mode hours (default 1 AM - 7 AM)
    night_hours = refresh_config.get("night_hours", {})
    night_start = night_hours.get("start", 1)
    night_end = night_hours.get("end", 7)

    # Check if it's night time (priority over presence)
    current_hour = datetime.now().hour
    is_night = False
    if night_start > night_end:  # Overnight period (e.g., 23-6)
        is_night = current_hour >= night_start or current_hour < night_end
    else:  # Same-day period (e.g., 1-7)
        is_night = night_start <= current_hour < night_end

    # Night mode takes priority
    if is_night:
        logger.info(f"🌙 Night mode active ({current_hour}:00 is between {night_start}:00-{night_end}:00) → {night_rate}s refresh")
        return night_rate

    # Check presence if enabled
    # Note: Waveshare display polls every 45s and writes to shared file.
    # We just read from that file - no blocking arp-scan in request path!
    if SharedPresenceState is not None:
        try:
            # Try reading from shared state file first
            is_home, timestamp, is_stale = SharedPresenceState.read_state()

            if is_home is not None and not is_stale:
                # Got fresh state from Waveshare
                if is_home:
                    logger.info(f"🏠 HOME (from Waveshare cache) → {fast_rate}s refresh ({fast_rate//60}min)")
                    return fast_rate
                else:
                    logger.info(f"🚪 AWAY (from Waveshare cache) → {slow_rate}s refresh ({slow_rate//60}min)")
                    return slow_rate

            # Shared state is stale or missing - fall back to direct detection
            logger.debug("Shared state stale/missing, falling back to direct detection")

        except Exception as e:
            logger.warning(f"Failed to read shared state: {e}")

    # Fallback: Direct detection (only if shared state unavailable)
    detector = get_presence_detector()
    if detector is not None:
        try:
            is_home = detector.is_anyone_home()
            if is_home:
                logger.info(f"🏠 HOME (fallback detection) → {fast_rate}s refresh ({fast_rate//60}min)")
                return fast_rate
            else:
                logger.info(f"🚪 AWAY (fallback detection) → {slow_rate}s refresh ({slow_rate//60}min)")
                return slow_rate
        except Exception as e:
            # FAIL-OPEN: On error, default to fast rate (assume home)
            # Better to refresh too often than miss updates when actually home
            logger.warning(f"⚠️  Presence detection failed, FAIL-OPEN to fast rate → {fast_rate}s refresh ({fast_rate//60}min)")
            logger.warning(f"    Exception: {e}")
            return fast_rate

    # No presence detection configured, use fast rate
    logger.info(f"No presence detection configured → {fast_rate}s refresh")
    return fast_rate


# ============ DATA ============
def get_weather(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "weather_code"],
            "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "forecast_days": 8,
        }
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except:
        return None


def get_subway(config):
    if not config:
        return None
    routes = config.get("routes", [])
    stop_ids = config.get("stop_ids", [config.get("stop_id")])
    if not isinstance(stop_ids, list):
        stop_ids = [stop_ids]
    res = {"uptown": [], "downtown": []}
    feeds = {}
    for r in routes:
        u = ROUTE_TO_FEED.get(r)
        if u:
            feeds.setdefault(u, []).append(r)
    try:
        for url, r_list in feeds.items():
            feed = NYCTFeed(url)
            for sid in stop_ids:
                for t in feed.filter_trips(headed_for_stop_id=f"{sid}N", underway=True):
                    if t.route_id in r_list:
                        for u in t.stop_time_updates:
                            if u.stop_id == f"{sid}N" and u.arrival:
                                m = int(
                                    (u.arrival - datetime.now()).total_seconds() / 60
                                )
                                if m >= 0:
                                    res["uptown"].append(
                                        {"route": t.route_id, "min": m}
                                    )
                                break
                for t in feed.filter_trips(headed_for_stop_id=f"{sid}S", underway=True):
                    if t.route_id in r_list:
                        for u in t.stop_time_updates:
                            if u.stop_id == f"{sid}S" and u.arrival:
                                m = int(
                                    (u.arrival - datetime.now()).total_seconds() / 60
                                )
                                if m >= 0:
                                    res["downtown"].append(
                                        {"route": t.route_id, "min": m}
                                    )
                                break
    except:
        pass
    res["uptown"].sort(key=lambda x: x["min"])
    res["downtown"].sort(key=lambda x: x["min"])
    return res


# ============ DRAWING HELPERS ============
def get_w_icon(code):
    if code in [0, 1]:
        return "☀"
    if code in [2, 3]:
        return "☁"
    if code in [45, 48]:
        return "≈"
    if code in [51, 53, 55, 61, 63, 65]:
        return "☂"
    if code in [71, 73, 75, 77]:
        return "❄"
    if code in [95, 96, 99]:
        return "⚡"
    return "?"


def text_size(draw, text, font):
    """Return (width, height) of text including its left/top bearing."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_centered_text(draw, x, y, text, font, fill=COLOR_BLACK, align="left"):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    ox = bbox[0]  # left bearing: subtract so glyphs center on x
    if align == "center":
        draw.text((x - ox - (w // 2), y), text, font=font, fill=fill)
    elif align == "right":
        draw.text((x - ox - w, y), text, font=font, fill=fill)
    else:
        draw.text((x, y), text, font=font, fill=fill)
    return w


BADGE_SIZE = 56  # diameter of the route badge circle


def draw_train_block(draw, x, y, train, font_bul, font_time, is_first=False):
    """Draw one train column: a filled route badge with the arrival time below.

    (x, y) is the top-left of the badge. The badge is a filled circle with
    the route letter/digit centered in white; the minutes ("Now" / "12m")
    are centered underneath. The first (soonest) train is emphasized in
    black, later ones in gray.
    """
    size = BADGE_SIZE
    cx = x + size // 2
    draw.ellipse([x, y, x + size, y + size], fill=COLOR_BLACK)

    route = train["route"]
    if len(route) > 1:
        f_badge = get_font(max(18, font_bul.size - 14), True)
    else:
        f_badge = font_bul
    bw, bh = text_size(draw, route, f_badge)
    draw.text(
        (cx - bw // 2, y + (size - bh) // 2),
        route,
        fill=COLOR_WHITE,
        font=f_badge,
    )

    text_color = COLOR_BLACK if is_first else COLOR_GRAY
    minutes_y = y + size + 6
    if train["min"] == 0:
        draw_centered_text(draw, cx, minutes_y, "Now", font_time, fill=text_color, align="center")
    else:
        draw_centered_text(draw, cx, minutes_y, f"{train['min']}m", font_time, fill=text_color, align="center")


# ============ OVERLAYS ============
# Regions that overlay slots may take over. Core data (time header, battery,
# next-refresh) is never covered except by "fullscreen".
OVERLAY_REGIONS = {
    "sidebar": (SIDEBAR_X, 115, 800, 360),  # right column (weather rating, reminders)
    "banner": (0, 360, 800, 480),        # forecast footer
    "fullscreen": (0, 115, 800, 480),    # everything below the header
}


def wrap_text(draw, text, font, max_width):
    """Word-wrap text to fit max_width. Returns list of lines."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def draw_overlay(img, draw, overlay):
    """Composite one overlay card into its slot region."""
    x0, y0, x1, y1 = OVERLAY_REGIONS[overlay["slot"]]
    w, h = x1 - x0, y1 - y0
    pad = 12

    # Clear the region and frame it so it reads as a deliberate card.
    draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=COLOR_WHITE)
    draw.rectangle([x0 + 2, y0 + 2, x1 - 3, y1 - 3], outline=COLOR_BLACK, width=2)

    content_x = x0 + pad
    content_w = w - 2 * pad
    cursor_y = y0 + pad

    # Optional image: on the left for wide slots, on top for the sidebar.
    image_path = overlay_store.get_image(overlay["id"]) if overlay.get("has_image") else None
    if image_path:
        try:
            art = Image.open(image_path).convert("L")
            if overlay["slot"] == "sidebar":
                max_art = (content_w, h // 2 - pad)
            elif overlay["slot"] == "fullscreen":
                # Text below if any; give the image most of the space.
                reserve = 70 if (overlay.get("title") or overlay.get("text")) else 0
                max_art = (content_w, h - 2 * pad - reserve)
            else:  # banner: image left, text right
                max_art = (h - 2 * pad, h - 2 * pad)
            art.thumbnail(max_art)
            if overlay["slot"] == "banner":
                img.paste(art, (content_x, y0 + (h - art.height) // 2))
                content_x += art.width + pad
                content_w -= art.width + pad
            else:
                img.paste(art, (x0 + (w - art.width) // 2, cursor_y))
                cursor_y += art.height + 8
        except Exception as e:
            logger.warning(f"Overlay {overlay['id']}: failed to render image: {e}")

    title = overlay.get("title") or ""
    text = overlay.get("text") or ""

    if overlay["slot"] == "sidebar":
        f_title, f_body = get_font(24, True), get_font(18)
    elif overlay["slot"] == "fullscreen":
        f_title, f_body = get_font(44, True), get_font(28)
    else:
        f_title, f_body = get_font(30, True), get_font(22)

    if title:
        title_step = getattr(f_title, "size", 24) + 4
        for line in wrap_text(draw, title, f_title, content_w):
            if cursor_y + getattr(f_title, "size", 24) > y1 - pad:
                break
            draw.text((content_x, cursor_y), line, font=f_title, fill=COLOR_BLACK)
            cursor_y += title_step
        cursor_y += 4
    if text:
        # Sidebar cards may contain the full weather report, not a manually
        # truncated excerpt. Fit the body font to the remaining card height;
        # other slots retain their normal, larger typography.
        if overlay["slot"] == "sidebar":
            for body_size in range(18, 11, -1):
                candidate_font = get_font(body_size)
                candidate_lines = wrap_text(draw, text, candidate_font, content_w)
                glyph_h = text_size(draw, "Ag", candidate_font)[1]
                candidate_step = glyph_h + 4
                last_y = cursor_y + max(0, len(candidate_lines) - 1) * candidate_step
                if last_y + glyph_h <= y1 - pad:
                    f_body = candidate_font
                    body_lines = candidate_lines
                    body_step = candidate_step
                    break
            else:
                body_lines = wrap_text(draw, text, f_body, content_w)
                body_step = text_size(draw, "Ag", f_body)[1] + 4
        else:
            body_lines = wrap_text(draw, text, f_body, content_w)
            body_step = getattr(f_body, "size", 20) + 4

        for line in body_lines:
            glyph_h = text_size(draw, "Ag", f_body)[1]
            if cursor_y + glyph_h > y1 - pad:
                break
            draw.text((content_x, cursor_y), line, font=f_body, fill=COLOR_BLACK)
            cursor_y += body_step


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


def draw_battery_icon(draw, x, y, percent, w=30, h=14):
    """Draw a small battery glyph; return its total width (incl. terminal)."""
    body_w = w - 3
    draw.rectangle([x, y, x + body_w, y + h], outline=COLOR_BLACK, width=1)
    tw, th = 3, 6
    draw.rectangle(
        [x + body_w, y + (h - th) // 2, x + body_w + tw, y + (h + th) // 2],
        fill=COLOR_BLACK,
    )
    if percent > 0:
        fw = max(1, int((body_w - 4) * percent / 100))
        draw.rectangle([x + 2, y + 2, x + 2 + fw, y + h - 2], fill=COLOR_BLACK)
    return body_w + tw


def draw_temp_pair(draw, cx, y, hi, lo, f_hi, f_lo):
    """Draw "HI° LO°" centered as a pair; low temp gray, baselines aligned."""
    hi_str = f"{hi}°"
    lo_str = f"{lo}°"
    w_hi = text_size(draw, hi_str, f_hi)[0]
    w_lo = text_size(draw, lo_str, f_lo)[0]
    gap = 10
    x = cx - (w_hi + gap + w_lo) // 2
    draw.text((x, y), hi_str, font=f_hi, fill=COLOR_BLACK)
    lo_y = y + max(0, getattr(f_hi, "size", 0) - getattr(f_lo, "size", 0))
    draw.text((x + w_hi + gap, lo_y), lo_str, font=f_lo, fill=COLOR_GRAY)


def draw_status_line(draw, center_x, y, battery_percent, next_refresh_str, font):
    """Centered header status line: battery % then the next-update time."""
    sep = "  ·  "
    batt_w = 30
    pct_str = f"{battery_percent}%" if battery_percent is not None else None
    pct_w = text_size(draw, pct_str, font)[0] if pct_str else 0
    sep_w = text_size(draw, sep, font)[0] if pct_str else 0
    next_w = text_size(draw, next_refresh_str, font)[0]
    parts_w = (batt_w + 5 + pct_w + sep_w + next_w) if pct_str else next_w

    x = center_x - parts_w // 2
    if pct_str:
        draw_battery_icon(draw, x, y + 1, battery_percent, w=batt_w, h=14)
        draw.text((x + batt_w + 5, y), pct_str, font=font, fill=COLOR_BLACK)
        x += batt_w + 5 + pct_w
        draw.text((x, y), sep, font=font, fill=COLOR_GRAY)
        x += sep_w
    draw.text((x, y), next_refresh_str, font=font, fill=COLOR_GRAY)


def generate_image(battery_percent=None, now=None, weather=None, subway=None, refresh_seconds=None):
    """Render the 800x480 dashboard.

    Weather/subway/time can be injected for deterministic tests; when omitted
    they are fetched live exactly as before, preserving the endpoint contract.
    """
    now = now or datetime.now()
    config = load_config()
    station = (config.get("stations") or config.get("stops", [{}]))[0]

    if weather is None:
        weather = get_weather(station.get("lat", 40.78), station.get("lon", -73.97))
    if subway is None:
        subway = get_subway(station)
    if refresh_seconds is None:
        refresh_seconds = calculate_refresh_rate()

    img = Image.new("L", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=COLOR_WHITE)
    draw = ImageDraw.Draw(img)

    # FONTS
    f_huge = get_font(68, True)       # time, current temp
    f_large = get_font(44, True)      # route badge letter
    f_med = get_font(28, True)        # AM/PM, date
    f_header = get_font(18, True)     # section labels
    f_small = get_font(20, True)      # forecast day + hi temp
    f_tiny = get_font(16)             # status line, low temp
    f_time = get_font(24, True)       # arrival minutes

    f_icon_lg = get_font(56, is_icon=True)
    f_icon_med = get_font(26, is_icon=True)

    # --- 1. HEADER (0 - 115): time/date left, weather right, status bottom ---
    # Time (left)
    w_time = draw_centered_text(draw, 20, 6, now.strftime("%I:%M").lstrip("0"), f_huge)
    draw.text((20 + w_time + 10, 44), now.strftime("%p"), font=f_med, fill=COLOR_GRAY)
    draw.text((22, 82), now.strftime("%A, %b %d"), font=f_med)

    # Current weather (right): icon + temperature
    if weather and "current" in weather:
        temp = f"{int(weather['current']['temperature_2m'])}°"
        icon = get_w_icon(weather["current"]["weather_code"])
        w_t = draw_centered_text(draw, DISPLAY_WIDTH - 20, 16, temp, f_huge, align="right")
        draw_centered_text(draw, DISPLAY_WIDTH - 20 - w_t - 12, 22, icon, f_icon_lg, align="right")

    # Status line (battery + next update), centered just above the divider
    next_refresh_time = (now + timedelta(seconds=refresh_seconds)).strftime("%I:%M %p").lstrip("0")
    next_refresh_str = f"Next update: {next_refresh_time}"
    draw_status_line(draw, DISPLAY_WIDTH // 2, 96, battery_percent, next_refresh_str, f_tiny)

    draw.line([(0, 115), (DISPLAY_WIDTH, 115)], fill=COLOR_BLACK, width=4)

    # --- 2. MAIN BODY (115 - 360): subway, kept left of the sidebar slot ---
    dirs = station.get("directions", {})
    # Four slots across the left 560px leave a wider 240px sidebar. This keeps
    # the weather-rating copy from wrapping into a clipped final line.
    slot_centers = [70, 210, 350, 490]
    badge = BADGE_SIZE

    lbl_up = dirs.get("uptown", "UP").split("(")[0].strip()
    draw.text((20, 120), lbl_up, font=f_header, fill=COLOR_GRAY)
    if subway and subway["uptown"]:
        for i, t in enumerate(subway["uptown"][:TRANSIT_TRAIN_COUNT]):
            draw_train_block(draw, slot_centers[i] - badge // 2, 146, t, f_large, f_time, is_first=(i == 0))

    lbl_down = dirs.get("downtown", "DOWN").split("(")[0].strip()
    draw.text((20, 242), lbl_down, font=f_header, fill=COLOR_GRAY)
    if subway and subway["downtown"]:
        for i, t in enumerate(subway["downtown"][:TRANSIT_TRAIN_COUNT]):
            draw_train_block(draw, slot_centers[i] - badge // 2, 266, t, f_large, f_time, is_first=(i == 0))

    # Make the reserved sidebar rail explicit without competing with core data.
    # Keep the rule at x=559 so sidebar overlays (x=560..800) never cover it.
    draw.line([(SIDEBAR_X - 1, 120), (SIDEBAR_X - 1, 355)], fill=COLOR_GRAY, width=1)

    # --- 3. FOOTER (360 - 480): 7-day forecast ---
    fy = 360
    draw.line([(0, fy), (DISPLAY_WIDTH, fy)], fill=COLOR_BLACK, width=3)
    draw.text((20, fy + 6), "FORECAST", font=f_tiny, fill=COLOR_GRAY)

    if weather and "daily" in weather:
        d = weather["daily"]
        col_w = DISPLAY_WIDTH / 7
        for i in range(0, 7):
            date_obj = now + timedelta(days=i)
            day_label = date_obj.strftime("%a")
            icon = get_w_icon(d["weather_code"][i])
            hi = int(d["temperature_2m_max"][i])
            lo = int(d["temperature_2m_min"][i])
            cx = (i * col_w) + (col_w / 2)

            draw_centered_text(draw, cx, fy + 30, day_label, f_small, align="center")
            draw_centered_text(draw, cx, fy + 52, icon, f_icon_med, align="center")
            draw_temp_pair(draw, cx, fy + 82, hi, lo, f_small, f_tiny)

    # --- OVERLAYS (agent-pushed cards; drawn last so they sit on top) ---
    apply_overlays(img, draw)

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
        status["configured_intervals"] = {
            "fast": intervals.get("fast", 1),
            "slow": intervals.get("slow", 30),
            "night": intervals.get("night", 30),
        }

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
    picks the change up on its next poll (~1 min when someone is home,
    up to 30 min when away or at night).
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
