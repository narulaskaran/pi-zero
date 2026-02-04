#!/usr/bin/env python3
"""
Subway Display Image Server

Generates 800x480 BMP images for the reTerminal E1001 e-ink display.
Reuses the existing config.yaml and MTA feed logic from get_train_times.py.

Run with: python subway_server.py
Access at: http://YOUR_PI_IP:5000/display.bmp

Dependencies (add to requirements.txt):
    flask
    pillow
"""

import io
from datetime import datetime
from pathlib import Path

import yaml
from flask import Flask, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
from nyct_gtfs import NYCTFeed

# Import the route mapping from existing code
from get_train_times import ROUTE_TO_FEED

app = Flask(__name__)

# ============ DISPLAY CONFIGURATION ============
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "DejaVuSans-Bold.ttf",
]
# ===============================================


def load_config():
    """Load configuration from config.yaml (same as get_train_times.py)."""
    script_dir = Path(__file__).parent
    config_path = script_dir / "config.yaml"

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


def get_font(size: int):
    """Load a font, trying multiple paths."""
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def get_train_arrivals(station_config) -> dict:
    """
    Fetch train arrivals for a station.
    Returns: {"uptown": [...], "downtown": [...]}
    Each list contains: [{"route": "B", "minutes": 3}, ...]
    """
    routes = station_config["routes"]

    # Support both single stop_id and multiple stop_ids
    stop_ids = station_config.get("stop_ids", [station_config.get("stop_id")])
    if not isinstance(stop_ids, list):
        stop_ids = [stop_ids]

    # Group routes by feed
    feed_to_routes = {}
    for route in routes:
        if route not in ROUTE_TO_FEED:
            continue
        feed_url = ROUTE_TO_FEED[route]
        if feed_url not in feed_to_routes:
            feed_to_routes[feed_url] = []
        feed_to_routes[feed_url].append(route)

    uptown_arrivals = []
    downtown_arrivals = []

    try:
        for feed_url, feed_routes in feed_to_routes.items():
            feed = NYCTFeed(feed_url)

            for stop_id_base in stop_ids:
                uptown_stop_id = f"{stop_id_base}N"
                downtown_stop_id = f"{stop_id_base}S"

                # Uptown trains
                uptown_trips = feed.filter_trips(
                    headed_for_stop_id=uptown_stop_id, underway=True
                )

                for trip in uptown_trips:
                    if trip.route_id not in routes:
                        continue
                    for update in trip.stop_time_updates:
                        if update.stop_id == uptown_stop_id and update.arrival:
                            minutes = int(
                                (update.arrival - datetime.now()).total_seconds() / 60
                            )
                            if minutes >= 0:
                                uptown_arrivals.append(
                                    {
                                        "route": trip.route_id,
                                        "minutes": minutes,
                                        "arrival": update.arrival,
                                    }
                                )
                            break

                # Downtown trains
                downtown_trips = feed.filter_trips(
                    headed_for_stop_id=downtown_stop_id, underway=True
                )

                for trip in downtown_trips:
                    if trip.route_id not in routes:
                        continue
                    for update in trip.stop_time_updates:
                        if update.stop_id == downtown_stop_id and update.arrival:
                            minutes = int(
                                (update.arrival - datetime.now()).total_seconds() / 60
                            )
                            if minutes >= 0:
                                downtown_arrivals.append(
                                    {
                                        "route": trip.route_id,
                                        "minutes": minutes,
                                        "arrival": update.arrival,
                                    }
                                )
                            break

        # Sort by arrival time
        uptown_arrivals.sort(key=lambda x: x["minutes"])
        downtown_arrivals.sort(key=lambda x: x["minutes"])

    except Exception as e:
        print(f"Error fetching train data: {e}")

    return {"uptown": uptown_arrivals, "downtown": downtown_arrivals}


def draw_subway_bullet(draw: ImageDraw, x: int, y: int, route: str, size: int = 55):
    """Draw a subway line bullet (circle with letter)."""
    draw.ellipse([x, y, x + size, y + size], fill="black", outline="black")

    font = get_font(int(size * 0.6))
    bbox = draw.textbbox((0, 0), route, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    text_x = x + (size - text_width) // 2
    text_y = y + (size - text_height) // 2 - 2

    draw.text((text_x, text_y), route, fill="white", font=font)


def generate_display_image() -> Image.Image:
    """Generate the subway display image based on config.yaml."""
    img = Image.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=1)  # 1-bit, white
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = get_font(42)
    font_time = get_font(64)
    font_small = get_font(24)
    font_direction = get_font(28)

    config = load_config()

    if not config:
        draw.text(
            (50, DISPLAY_HEIGHT // 2),
            "Config error - check config.yaml",
            fill="black",
            font=font_small,
        )
        return img

    stations = config.get("stations", config.get("stops", []))

    if not stations:
        draw.text(
            (50, DISPLAY_HEIGHT // 2),
            "No stations configured",
            fill="black",
            font=font_small,
        )
        return img

    # For now, display the first station (can extend later for multiple)
    station = stations[0]
    station_name = station["name"]
    directions = station.get("directions", {"uptown": "UPTOWN", "downtown": "DOWNTOWN"})

    # Fetch arrivals
    arrivals = get_train_arrivals(station)

    # Draw header
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")

    # Truncate station name if too long
    display_name = station_name if len(station_name) < 35 else station_name[:32] + "..."
    draw.text((20, 12), display_name, fill="black", font=font_title)
    draw.text((DISPLAY_WIDTH - 140, 18), time_str, fill="black", font=font_small)

    # Separator
    draw.line([(20, 65), (DISPLAY_WIDTH - 20, 65)], fill="black", width=3)

    y_pos = 80

    # Uptown section
    uptown_label = directions.get("uptown", "UPTOWN")
    # Simplify long direction labels
    if len(uptown_label) > 20:
        uptown_label = uptown_label.split("(")[0].strip()
    draw.text((20, y_pos), f"↑ {uptown_label}", fill="black", font=font_direction)
    y_pos += 40

    uptown = arrivals["uptown"][:3]  # Max 3 trains per direction
    if uptown:
        for train in uptown:
            draw_subway_bullet(draw, 30, y_pos, train["route"])
            mins = train["minutes"]
            time_text = "Now" if mins == 0 else f"{mins} min"
            draw.text((100, y_pos + 8), time_text, fill="black", font=font_time)
            y_pos += 65
    else:
        draw.text((100, y_pos), "No trains", fill="black", font=font_small)
        y_pos += 40

    # Separator
    y_pos += 5
    draw.line([(20, y_pos), (DISPLAY_WIDTH - 20, y_pos)], fill="black", width=2)
    y_pos += 15

    # Downtown section
    downtown_label = directions.get("downtown", "DOWNTOWN")
    if len(downtown_label) > 20:
        downtown_label = downtown_label.split("(")[0].strip()
    draw.text((20, y_pos), f"↓ {downtown_label}", fill="black", font=font_direction)
    y_pos += 40

    downtown = arrivals["downtown"][:3]
    if downtown:
        for train in downtown:
            draw_subway_bullet(draw, 30, y_pos, train["route"])
            mins = train["minutes"]
            time_text = "Now" if mins == 0 else f"{mins} min"
            draw.text((100, y_pos + 8), time_text, fill="black", font=font_time)
            y_pos += 65
    else:
        draw.text((100, y_pos), "No trains", fill="black", font=font_small)

    # Footer
    draw.line(
        [(20, DISPLAY_HEIGHT - 45), (DISPLAY_WIDTH - 20, DISPLAY_HEIGHT - 45)],
        fill="black",
        width=2,
    )
    draw.text(
        (20, DISPLAY_HEIGHT - 35),
        f"Updated: {now.strftime('%I:%M:%S %p')}",
        fill="black",
        font=font_small,
    )

    return img


@app.route("/")
def index():
    """Health check with links."""
    return """
    <html>
    <head><title>Subway Display Server</title></head>
    <body>
        <h1>Subway Display Server</h1>
        <ul>
            <li><a href="/display.bmp">/display.bmp</a> - BMP for e-ink</li>
            <li><a href="/display.png">/display.png</a> - PNG preview</li>
            <li><a href="/status">/status</a> - JSON status</li>
        </ul>
    </body>
    </html>
    """


@app.route("/display.bmp")
def display_bmp():
    """Serve the display image as BMP."""
    img = generate_display_image()
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    buf.seek(0)
    return send_file(buf, mimetype="image/bmp", download_name="display.bmp")


@app.route("/display.png")
def display_png():
    """Serve PNG preview for browser viewing."""
    img = generate_display_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name="display.png")


@app.route("/status")
def status():
    """Return JSON status."""
    config = load_config()
    stations = config.get("stations", config.get("stops", [])) if config else []

    result = {"status": "ok", "timestamp": datetime.now().isoformat(), "stations": []}

    for station in stations:
        arrivals = get_train_arrivals(station)
        result["stations"].append(
            {
                "name": station["name"],
                "stop_id": station.get("stop_id"),
                "routes": station.get("routes"),
                "uptown": [
                    {"route": t["route"], "minutes": t["minutes"]}
                    for t in arrivals["uptown"][:5]
                ],
                "downtown": [
                    {"route": t["route"], "minutes": t["minutes"]}
                    for t in arrivals["downtown"][:5]
                ],
            }
        )

    return jsonify(result)


if __name__ == "__main__":
    config = load_config()
    if config:
        stations = config.get("stations", config.get("stops", []))
        print("=" * 50)
        print("Subway Display Image Server")
        print("=" * 50)
        for station in stations:
            print(f"  Station: {station['name']}")
            print(f"  Routes:  {station['routes']}")
        print()
        print("Endpoints:")
        print("  /display.bmp  - BMP for e-ink display")
        print("  /display.png  - PNG preview")
        print("  /status       - JSON status")
        print("=" * 50)

    app.run(host="0.0.0.0", port=5000, debug=False)
