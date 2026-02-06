#!/bin/bash
#
# OTA Upload Script for reTerminal Subway Display
#
# This script compiles and uploads the Arduino sketch to a reTerminal device
# over the network using OTA (Over-The-Air) updates.
#
# ⚠️  WARNING: Requires significant RAM for ESP32 compilation!
#     - Raspberry Pi Zero (512MB): NOT SUPPORTED - use laptop/desktop instead
#     - Raspberry Pi 3/4/5: Supported
#     - Laptop/Desktop: Recommended
#
# Usage:
#   ./upload-ota.sh [hostname_or_ip]
#
# Examples:
#   ./upload-ota.sh                           # Uses default hostname
#   ./upload-ota.sh reterminal-display.local  # Custom hostname
#   ./upload-ota.sh 192.168.0.100             # IP address
#

set -e  # Exit on error

# Check if running on Pi Zero
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    if echo "$MODEL" | grep -qi "Pi Zero"; then
        echo "⚠️  ERROR: Running on Raspberry Pi Zero"
        echo "This device has insufficient RAM for ESP32 compilation."
        echo ""
        echo "Please use your laptop/desktop for OTA updates instead:"
        echo "  arduino-cli compile --fqbn esp32:esp32:esp32s3 ."
        echo "  arduino-cli upload --fqbn esp32:esp32:esp32s3 -p $1 ."
        echo ""
        echo "Or use Arduino IDE: Tools → Port → Network Ports → reterminal-display"
        exit 1
    fi
fi

# Configuration
DEFAULT_HOSTNAME="reterminal-display.local"
SKETCH_DIR="$(cd "$(dirname "$0")/reterminal-sketch" && pwd)"
SKETCH_FILE="$SKETCH_DIR/reterminal-sketch.ino"
FQBN="esp32:esp32:esp32s3"

# Get hostname from argument or use default
HOSTNAME="${1:-$DEFAULT_HOSTNAME}"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Verify prerequisites
if ! command -v arduino-cli &> /dev/null; then
    error "arduino-cli not found. Please install it first:"
    echo "  https://arduino.github.io/arduino-cli/latest/installation/"
    exit 1
fi

if [ ! -f "$SKETCH_FILE" ]; then
    error "Sketch file not found: $SKETCH_FILE"
    exit 1
fi

info "Starting OTA upload to $HOSTNAME"

# Compile the sketch
info "Compiling sketch..."
if ! arduino-cli compile --fqbn "$FQBN" "$SKETCH_DIR"; then
    error "Compilation failed"
    exit 1
fi

info "Compilation successful"

# Upload via OTA
info "Uploading to $HOSTNAME via OTA..."
info "Make sure the device is powered on and connected to WiFi"

if arduino-cli upload --fqbn "$FQBN" -p "$HOSTNAME" "$SKETCH_DIR"; then
    info "Upload successful!"
    info "The device should restart and begin running the new firmware"
else
    error "Upload failed"
    warn "Troubleshooting steps:"
    echo "  1. Verify the device is powered on and connected to WiFi"
    echo "  2. Check that OTA_ENABLED is set to true in the sketch"
    echo "  3. Ensure the hostname/IP is correct: $HOSTNAME"
    echo "  4. Try pinging the device: ping $HOSTNAME"
    echo "  5. Check that OTA_WAIT_SECONDS allows enough time for connection"
    exit 1
fi
