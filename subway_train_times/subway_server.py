#!/usr/bin/env python3
"""
Subway Dashboard - 1-Bit Dithered Fix
"""

import io
import os
from datetime import datetime, timedelta
from pathlib import Path

import yaml
import requests
import yfinance as yf
from flask import Flask, send_file, request, jsonify
from PIL import Image, ImageDraw, ImageFont
from nyct_gtfs import NYCTFeed

try:
    from get_train_times import ROUTE_TO_FEED
except ImportError:
    ROUTE_TO_FEED = {}

try:
    from presence_detector import PresenceDetector
except ImportError:
    PresenceDetector = None

app = Flask(__name__)

# ============ CONFIG ============
# Global presence detector (initialized on first use)
_presence_detector = None
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

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
            _presence_detector = PresenceDetector(mac_addresses=devices)
    return _presence_detector


def calculate_refresh_rate():
    """
    Calculate the appropriate refresh rate in seconds based on:
    - Time of day (night mode)
    - Device presence (someone home)

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
        return night_rate

    # Check presence if enabled
    detector = get_presence_detector()
    if detector is not None:
        try:
            is_home = detector.is_anyone_home()
            return fast_rate if is_home else slow_rate
        except Exception:
            # On error, default to slow rate
            return slow_rate

    # No presence detection configured, use fast rate
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


def get_finance():
    data = []
    try:
        tickers = {"^GSPC": "S&P", "BTC-USD": "BTC", "GC=F": "Gold"}
        t_obj = yf.Tickers(" ".join(tickers.keys()))
        for sym, label in tickers.items():
            info = t_obj.tickers[sym].fast_info
            if info.last_price:
                pct = (
                    (info.last_price - info.previous_close) / info.previous_close
                ) * 100
                data.append({"label": label, "price": info.last_price, "change": pct})
    except:
        pass
    return data


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


def draw_centered_text(draw, x, y, text, font, fill=COLOR_BLACK, align="left"):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    if align == "center":
        draw.text((x - (w // 2), y), text, font=font, fill=fill)
    elif align == "right":
        draw.text((x - w, y), text, font=font, fill=fill)
    else:
        draw.text((x, y), text, font=font, fill=fill)
    return w


def draw_train_block(draw, x, y, train, font_bul, font_time, is_first=False):
    size = 56
    draw.ellipse([x, y, x + size, y + size], fill=COLOR_BLACK)

    bw = draw.textbbox((0, 0), train["route"], font=font_bul)[2]
    draw.text((x + (size - bw) / 2, y), train["route"], fill=COLOR_WHITE, font=font_bul)

    text_color = COLOR_BLACK if is_first else COLOR_GRAY
    text_y = y + 60

    if train["min"] == 0:
        draw_centered_text(
            draw,
            x + (size // 2),
            text_y,
            "Now",
            font_time,
            fill=text_color,
            align="center",
        )
    else:
        full_str = f"{train['min']}m"
        draw_centered_text(
            draw,
            x + (size // 2),
            text_y,
            full_str,
            font_time,
            fill=text_color,
            align="center",
        )


def generate_image(battery_percent=None):
    img = Image.new("L", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=COLOR_WHITE)
    draw = ImageDraw.Draw(img)

    # FONTS
    f_huge = get_font(68, True)
    f_large = get_font(48, True)
    f_med = get_font(28, True)

    # New Smaller Header Font (24px instead of 28px)
    f_header = get_font(24, True)

    f_small = get_font(20, True)
    f_tiny = get_font(16)

    f_icon_lg = get_font(60, is_icon=True)
    f_icon_med = get_font(28, is_icon=True)
    f_icon_sm = get_font(20, is_icon=True)

    # --- 1. HEADER (0 - 115) ---
    now = datetime.now()
    w_time = draw_centered_text(draw, 20, 10, now.strftime("%I:%M").lstrip("0"), f_huge)
    draw.text((20 + w_time + 8, 58), now.strftime("%p"), font=f_med, fill=COLOR_GRAY)
    draw.text((22, 80), now.strftime("%A, %b %d"), font=f_med)

    config = load_config()
    station = (config.get("stations") or config.get("stops", [{}]))[0]
    weather = get_weather(station.get("lat", 40.78), station.get("lon", -73.97))

    if weather and "current" in weather:
        temp = f"{int(weather['current']['temperature_2m'])}°"
        icon = get_w_icon(weather["current"]["weather_code"])
        w_t = draw_centered_text(
            draw, DISPLAY_WIDTH - 20, 20, temp, f_huge, align="right"
        )
        draw_centered_text(
            draw, DISPLAY_WIDTH - 20 - w_t - 10, 15, icon, f_icon_lg, align="right"
        )

    draw.line([(0, 115), (DISPLAY_WIDTH, 115)], fill=COLOR_BLACK, width=4)

    # --- 2. MAIN BODY (115 - 360) ---
    draw.line([(600, 115), (600, 360)], fill=COLOR_BLACK, width=3)

    subway = get_subway(station)
    dirs = station.get("directions", {})
    slot_centers = [75, 225, 375, 525]

    # === UPTOWN ===
    lbl_up = dirs.get("uptown", "UP").split("(")[0].strip()
    draw.text((20, 122), lbl_up, font=f_header, fill=COLOR_GRAY)

    if subway and subway["uptown"]:
        for i, t in enumerate(subway["uptown"][:4]):
            center_x = slot_centers[i]
            # y=148 slightly nudged down
            draw_train_block(
                draw, center_x - 28, 148, t, f_large, f_med, is_first=(i == 0)
            )

    # === DOWNTOWN ===
    lbl_down = dirs.get("downtown", "DOWN").split("(")[0].strip()
    draw.text((20, 245), lbl_down, font=f_header, fill=COLOR_GRAY)

    if subway and subway["downtown"]:
        for i, t in enumerate(subway["downtown"][:4]):
            center_x = slot_centers[i]
            # y=270 ensures the bottom is clear
            draw_train_block(
                draw, center_x - 28, 270, t, f_large, f_med, is_first=(i == 0)
            )

    # === FINANCE COLUMN ===
    fin = get_finance()
    fin_center_x = 700
    fin_y = 125

    for f in fin:
        is_up = f["change"] >= 0
        sym = "▲" if is_up else "▼"

        draw_centered_text(
            draw, fin_center_x, fin_y, f.get("label"), f_med, align="center"
        )

        pct_str = f"{abs(f['change']):.1f}%"
        aw = draw.textbbox((0, 0), sym, font=f_icon_med)[2]
        pw = draw.textbbox((0, 0), pct_str, font=f_med)[2]
        total_w = aw + 4 + pw
        start_x = fin_center_x - (total_w // 2)

        draw.text((start_x, fin_y + 26), sym, font=f_icon_med, fill=COLOR_BLACK)
        draw.text((start_x + aw + 4, fin_y + 26), pct_str, font=f_med, fill=COLOR_BLACK)

        if f["label"] == "BTC":
            p = f"{f['price']/1000:.1f}k"
        elif f["price"] > 100:
            p = f"{f['price']:.0f}"
        else:
            p = f"{f['price']:.1f}"

        draw_centered_text(
            draw, fin_center_x, fin_y + 54, p, f_small, fill=COLOR_GRAY, align="center"
        )

        fin_y += 75

    # --- 3. FOOTER (360 - 480) ---
    fy = 360
    draw.line([(0, fy), (DISPLAY_WIDTH, fy)], fill=COLOR_BLACK, width=3)

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

            draw_centered_text(draw, cx, fy + 10, day_label, f_small, align="center")
            draw_centered_text(draw, cx, fy + 35, icon, f_icon_med, align="center")
            draw_centered_text(draw, cx - 12, fy + 75, f"{hi}°", f_med, align="center")
            draw.text((cx + 12, fy + 82), f"{lo}°", font=f_tiny, fill=COLOR_GRAY)

    # --- BATTERY INDICATOR (top middle, subtle) ---
    if battery_percent is not None:
        batt_x = (DISPLAY_WIDTH // 2) - 30  # Center horizontally
        batt_y = 8  # Top, subtle positioning

        # Battery icon (simple rectangle with terminal)
        battery_width = 50
        battery_height = 20
        terminal_width = 4
        terminal_height = 10

        # Draw battery body
        draw.rectangle(
            [batt_x, batt_y, batt_x + battery_width, batt_y + battery_height],
            outline=COLOR_BLACK,
            width=2
        )

        # Draw battery terminal
        draw.rectangle(
            [
                batt_x + battery_width,
                batt_y + (battery_height - terminal_height) // 2,
                batt_x + battery_width + terminal_width,
                batt_y + (battery_height + terminal_height) // 2
            ],
            fill=COLOR_BLACK
        )

        # Fill battery based on percentage
        if battery_percent > 0:
            fill_width = int((battery_width - 6) * battery_percent / 100)
            draw.rectangle(
                [batt_x + 3, batt_y + 3, batt_x + 3 + fill_width, batt_y + battery_height - 3],
                fill=COLOR_BLACK
            )

        # Draw percentage text
        batt_text = f"{battery_percent}%"
        draw.text((batt_x + battery_width + terminal_width + 6, batt_y + 2), batt_text, font=f_tiny, fill=COLOR_BLACK)

    # --- NEXT REFRESH TIME (top center, above battery) ---
    refresh_minutes = calculate_refresh_rate()
    next_refresh_time = datetime.now() + timedelta(minutes=refresh_minutes)
    next_refresh_str = next_refresh_time.strftime("Next update: %I:%M %p")

    # Calculate text position for center alignment
    bbox = draw.textbbox((0, 0), next_refresh_str, font=f_tiny)
    text_width = bbox[2] - bbox[0]
    refresh_x = (DISPLAY_WIDTH - text_width) // 2
    refresh_y = 30  # Top, below battery indicator

    draw.text((refresh_x, refresh_y), next_refresh_str, font=f_tiny, fill=COLOR_BLACK)

    return img


@app.route("/refresh-rate")
def get_refresh_rate():
    """Return the current refresh rate in seconds as JSON."""
    try:
        refresh_rate = calculate_refresh_rate()
        return jsonify({"refresh_rate": refresh_rate})
    except Exception as e:
        # On error, return a safe default
        return jsonify({"refresh_rate": 120, "error": str(e)}), 500


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

    print(f"Starting Flask server on {host}:{port}")
    app.run(host=host, port=port)
