#!/usr/bin/env python3
"""
Display Renderer for 250×122 E-Paper Display

Optimized layout for Raspberry Pi system monitoring.
Shows: CPU temp, time, RAM usage, WiFi status, home/away status.
"""

from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


class SystemRenderer:
    """
    Renders system stats for 250×122 e-Paper display.

    Layout (250×122):
    - Top: Time + Date (35px)
    - Middle: CPU temp, RAM, WiFi (65px)
    - Bottom: Presence status (22px)
    """

    WIDTH = 250
    HEIGHT = 122

    def __init__(self):
        """Initialize the renderer with fonts."""
        self.fonts = self._load_fonts()

    def _load_fonts(self):
        """Load fonts with fallbacks."""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            str(Path(__file__).parent.parent / "subway_train_times" / "Roboto-Bold.ttf"),
        ]

        fonts = {}
        for size_name, size in [("huge", 32), ("large", 24), ("medium", 16), ("small", 12), ("tiny", 10)]:
            fonts[size_name] = None
            for path in font_paths:
                try:
                    fonts[size_name] = ImageFont.truetype(path, size)
                    break
                except:
                    continue
            if fonts[size_name] is None:
                fonts[size_name] = ImageFont.load_default()

        return fonts

    def render_system_stats(self, stats):
        """
        Render system statistics.

        Args:
            stats: dict from SystemMonitor.get_all_stats()
                {
                    "cpu_temp": 45.2,
                    "ram": {"percent": 35.5, "used_mb": 512, "total_mb": 1024},
                    "wifi": {"connected": True, "ssid": "MyNet", "signal": -45},
                    "is_home": True
                }

        Returns:
            PIL Image object (250×122, mode '1')
        """
        # Create blank white image
        image = Image.new('1', (self.WIDTH, self.HEIGHT), 255)
        draw = ImageDraw.Draw(image)

        # === HEADER: Time + Date ===
        now = datetime.now()
        time_str = now.strftime("%I:%M").lstrip("0")
        am_pm = now.strftime("%p")
        date_str = now.strftime("%a %b %d")

        # Draw time (left side)
        draw.text((4, 2), time_str, font=self.fonts["huge"], fill=0)

        # Draw AM/PM smaller next to time
        time_bbox = draw.textbbox((4, 2), time_str, font=self.fonts["huge"])
        time_width = time_bbox[2] - time_bbox[0]
        draw.text((time_width + 8, 8), am_pm, font=self.fonts["small"], fill=0)

        # Draw date (right side)
        date_bbox = draw.textbbox((0, 0), date_str, font=self.fonts["small"])
        date_width = date_bbox[2] - date_bbox[0]
        draw.text((self.WIDTH - date_width - 4, 4), date_str, font=self.fonts["small"], fill=0)

        # Divider line
        draw.line([(0, 37), (self.WIDTH, 37)], fill=0, width=1)

        # === MIDDLE: System Stats (3 columns) ===
        middle_y = 42
        col_width = self.WIDTH // 3

        # Column 1: CPU Temperature
        cpu_temp = stats.get("cpu_temp")
        if cpu_temp is not None:
            temp_str = f"{cpu_temp:.1f}°C"
            draw.text((8, middle_y), "CPU", font=self.fonts["tiny"], fill=0)
            draw.text((8, middle_y + 12), temp_str, font=self.fonts["large"], fill=0)
        else:
            draw.text((8, middle_y), "CPU", font=self.fonts["tiny"], fill=0)
            draw.text((8, middle_y + 12), "N/A", font=self.fonts["medium"], fill=0)

        # Column 2: RAM Usage
        ram = stats.get("ram", {})
        ram_percent = ram.get("percent", 0)
        ram_str = f"{ram_percent:.0f}%"
        draw.text((col_width + 8, middle_y), "RAM", font=self.fonts["tiny"], fill=0)
        draw.text((col_width + 8, middle_y + 12), ram_str, font=self.fonts["large"], fill=0)

        # Draw RAM bar graph (mini)
        bar_x = col_width + 8
        bar_y = middle_y + 40
        bar_width = 50
        bar_height = 8
        draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)], outline=0, width=1)
        fill_width = int(bar_width * (ram_percent / 100))
        if fill_width > 0:
            draw.rectangle([(bar_x + 1, bar_y + 1), (bar_x + fill_width - 1, bar_y + bar_height - 1)], fill=0)

        # Column 3: WiFi Status
        wifi = stats.get("wifi", {})
        wifi_connected = wifi.get("connected", False)
        wifi_ssid = wifi.get("ssid", "")

        draw.text((col_width * 2 + 8, middle_y), "WiFi", font=self.fonts["tiny"], fill=0)

        if wifi_connected:
            # Truncate SSID if too long
            ssid_display = wifi_ssid[:8] if len(wifi_ssid) > 8 else wifi_ssid
            draw.text((col_width * 2 + 8, middle_y + 12), ssid_display, font=self.fonts["medium"], fill=0)

            # WiFi signal indicator (simple bars)
            signal = wifi.get("signal")
            if signal is not None:
                # Convert dBm to bars (rough approximation)
                # -30 to -50: Excellent (4 bars)
                # -50 to -60: Good (3 bars)
                # -60 to -70: Fair (2 bars)
                # -70+: Poor (1 bar)
                if signal >= -50:
                    bars = 4
                elif signal >= -60:
                    bars = 3
                elif signal >= -70:
                    bars = 2
                else:
                    bars = 1

                # Draw signal bars
                bar_x = col_width * 2 + 8
                bar_y_base = middle_y + 35
                for i in range(4):
                    bar_height = 4 + (i * 3)
                    if i < bars:
                        draw.rectangle([
                            (bar_x + i * 6, bar_y_base - bar_height),
                            (bar_x + i * 6 + 4, bar_y_base)
                        ], fill=0)
                    else:
                        draw.rectangle([
                            (bar_x + i * 6, bar_y_base - bar_height),
                            (bar_x + i * 6 + 4, bar_y_base)
                        ], outline=0, width=1)
        else:
            draw.text((col_width * 2 + 8, middle_y + 12), "No WiFi", font=self.fonts["small"], fill=0)

        # Divider line
        footer_y = 100
        draw.line([(0, footer_y), (self.WIDTH, footer_y)], fill=0, width=1)

        # === FOOTER: Presence Status ===
        is_home = stats.get("is_home")

        if is_home is not None:
            status_text = "🏠 HOME" if is_home else "🚶 AWAY"
            # Use simpler text since emoji might not render
            status_text = "HOME" if is_home else "AWAY"

            # Center the status text
            status_bbox = draw.textbbox((0, 0), status_text, font=self.fonts["medium"])
            status_width = status_bbox[2] - status_bbox[0]
            draw.text(((self.WIDTH - status_width) // 2, footer_y + 5), status_text, font=self.fonts["medium"], fill=0)
        else:
            # No presence detection configured
            status_text = "Pi Stats"
            status_bbox = draw.textbbox((0, 0), status_text, font=self.fonts["small"])
            status_width = status_bbox[2] - status_bbox[0]
            draw.text(((self.WIDTH - status_width) // 2, footer_y + 6), status_text, font=self.fonts["small"], fill=0)

        return image

    def render_error(self, error_message):
        """
        Render an error message.

        Args:
            error_message: Error text to display

        Returns:
            PIL Image object (250×122, mode '1')
        """
        image = Image.new('1', (self.WIDTH, self.HEIGHT), 255)
        draw = ImageDraw.Draw(image)

        # Draw border
        draw.rectangle([(2, 2), (self.WIDTH - 2, self.HEIGHT - 2)], outline=0, width=2)

        # Draw error icon (simple X)
        draw.line([(20, 20), (40, 40)], fill=0, width=3)
        draw.line([(40, 20), (20, 40)], fill=0, width=3)

        # Draw "ERROR" text
        draw.text((50, 20), "ERROR", font=self.fonts["large"], fill=0)

        # Draw error message (wrapped)
        words = error_message.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            if len(test_line) <= 30:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # Draw up to 3 lines
        y = 50
        for line in lines[:3]:
            draw.text((10, y), line, font=self.fonts["small"], fill=0)
            y += 15

        return image


if __name__ == "__main__":
    """Test the renderer."""
    renderer = SystemRenderer()

    # Test system stats display
    test_stats = {
        "cpu_temp": 45.8,
        "ram": {"percent": 62.5, "used_mb": 640, "total_mb": 1024},
        "wifi": {"connected": True, "ssid": "MyNetwork", "signal": -52},
        "is_home": True
    }

    image = renderer.render_system_stats(test_stats)
    image.save("/tmp/test_system_stats.png")
    print("Saved test image to /tmp/test_system_stats.png")

    # Test error display
    error_image = renderer.render_error("Failed to read CPU temperature sensor")
    error_image.save("/tmp/test_error.png")
    print("Saved error image to /tmp/test_error.png")
