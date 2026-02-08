#!/usr/bin/env python3
"""
Waveshare E-Paper Driver Wrapper

Provides a unified interface for Waveshare 2.13" e-Paper HAT (non-touch versions).
Uses the waveshare_epd library installed on the Pi.
"""

import sys
import os
from pathlib import Path

# Add Waveshare driver directory to Python path
EPAPER_LIB = Path.home() / "e-Paper" / "RaspberryPi_JetsonNano" / "python" / "lib"
if EPAPER_LIB.exists():
    sys.path.insert(0, str(EPAPER_LIB))

try:
    from waveshare_epd import epdconfig
except ImportError:
    print(f"Error: Waveshare driver library not found at {EPAPER_LIB}")
    print("Please install the Waveshare e-Paper library first.")
    print("Download from: https://github.com/waveshare/e-Paper")
    sys.exit(1)


class EPaperDisplay:
    """
    Unified interface for Waveshare 2.13" E-Paper HAT.

    Supports V2, V3, and V4 hardware versions with automatic driver selection.
    """

    # Display specifications
    WIDTH = 122   # Physical width (rotated 90°)
    HEIGHT = 250  # Physical height (rotated 90°)

    def __init__(self, version="V3"):
        """
        Initialize the e-Paper display.

        Args:
            version: Hardware version - "V2", "V3", or "V4"
        """
        self.version = version.upper()
        self.epd = None
        self.initialized = False
        self.partial_refresh_count = 0
        self.max_partial_refreshes = 10  # Full refresh after this many partial

        # Import the appropriate driver
        if self.version == "V2":
            from waveshare_epd import epd2in13_V2
            self.epd_module = epd2in13_V2
        elif self.version == "V3":
            from waveshare_epd import epd2in13_V3
            self.epd_module = epd2in13_V3
        elif self.version == "V4":
            from waveshare_epd import epd2in13_V4
            self.epd_module = epd2in13_V4
        else:
            raise ValueError(f"Unknown display version: {version}. Use V2, V3, or V4")

    def init(self):
        """Initialize the display hardware."""
        if not self.initialized:
            self.epd = self.epd_module.EPD()
            self.epd.init()
            self.initialized = True

    def clear(self):
        """Clear the display to white."""
        if not self.initialized:
            self.init()
        self.epd.Clear(0xFF)

    def display(self, image):
        """
        Display an image on the e-Paper screen.

        Args:
            image: PIL Image object (mode '1' for B&W)
        """
        if not self.initialized:
            self.init()

        # Convert to 1-bit if not already
        if image.mode != '1':
            image = image.convert('1')

        # Full display update
        self.epd.display(self.epd.getbuffer(image))
        self.partial_refresh_count = 0

    def display_partial(self, image):
        """
        Display using partial refresh (faster, less flicker).

        Only available on V2/V3. Falls back to full refresh on V4.
        Automatically does full refresh every N partial updates to prevent ghosting.

        Args:
            image: PIL Image object (mode '1' for B&W)
        """
        if not self.initialized:
            self.init()

        # Convert to 1-bit if not already
        if image.mode != '1':
            image = image.convert('1')

        # Check if we need a full refresh
        if self.partial_refresh_count >= self.max_partial_refreshes:
            print(f"Performing full refresh (after {self.partial_refresh_count} partial refreshes)")
            self.display(image)
            return

        # V4 doesn't support partial refresh reliably, fallback to full
        if self.version == "V4":
            self.display(image)
            return

        # V2/V3 partial refresh
        if self.partial_refresh_count == 0:
            # First partial refresh needs base image
            self.epd.displayPartBaseImage(self.epd.getbuffer(image))

        self.epd.displayPartial(self.epd.getbuffer(image))
        self.partial_refresh_count += 1

    def sleep(self):
        """Put the display into low-power sleep mode."""
        if self.initialized:
            self.epd.sleep()

    def cleanup(self):
        """
        Clean up and release hardware resources.

        Call this before exiting your program to prevent GPIO errors.
        """
        if self.initialized:
            self.epd.sleep()
            epdconfig.module_exit()
            self.initialized = False

    def __enter__(self):
        """Context manager support."""
        self.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.cleanup()


if __name__ == "__main__":
    """Test the display with a simple pattern."""
    from PIL import Image, ImageDraw, ImageFont

    print("Testing Waveshare 2.13\" E-Paper Display...")

    # Create test image
    image = Image.new('1', (EPaperDisplay.HEIGHT, EPaperDisplay.WIDTH), 255)
    draw = ImageDraw.Draw(image)

    # Draw border
    draw.rectangle([(0, 0), (249, 121)], outline=0, width=2)

    # Draw text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        font = ImageFont.load_default()

    draw.text((10, 10), "Waveshare Test", font=font, fill=0)
    draw.text((10, 40), "250x122 pixels", font=font, fill=0)
    draw.text((10, 70), "E-Paper HAT", font=font, fill=0)

    # Display test image
    with EPaperDisplay(version="V3") as epd:
        print("Clearing display...")
        epd.clear()

        print("Displaying test image...")
        epd.display(image)

        print("Display test complete!")
        print("Image should remain on screen even after script exits.")
