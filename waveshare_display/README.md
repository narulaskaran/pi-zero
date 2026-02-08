# Waveshare 2.13" E-Paper Display - Pi Stats Monitor

Real-time system monitoring display for Raspberry Pi using Waveshare 2.13" E-Paper HAT.

Shows:
- **Current time** and date
- **CPU temperature** in °C
- **RAM usage** with percentage and visual bar graph
- **WiFi status** with SSID and signal strength indicators
- **Presence detection** (HOME/AWAY) based on device proximity

## Hardware Specifications

- **Display**: 250×122 pixels, monochrome (black/white)
- **Interface**: SPI (display control)
- **Refresh**: ~2 seconds full refresh, ~0.3s partial refresh
- **Power**: Powered by Pi GPIO (no battery)
- **Model**: Waveshare 2.13inch E-Paper HAT (V2/V3/V4 supported)

## Setup Instructions

### 1. Hardware Connection

The HAT connects directly to the Pi's 40-pin GPIO header. No wiring needed!

Simply place the HAT on top of your Pi's GPIO pins.

### 2. Enable SPI Interface

```bash
sudo raspi-config
# Navigate to: Interfacing Options → SPI → Yes
# Reboot when prompted
sudo reboot
```

### 3. Install Waveshare Drivers

```bash
# Download Waveshare e-Paper library
cd ~
git clone https://github.com/waveshare/e-Paper.git

# Navigate to Python examples to verify installation
cd ~/e-Paper/RaspberryPi_JetsonNano/python/examples
```

### 4. Install Python Dependencies

```bash
# System dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil python3-numpy

# Python packages
cd ~/pi-zero/waveshare_display
pip3 install -r requirements.txt

# SPI library (requires sudo)
sudo pip3 install spidev
```

### 5. Configure Your Display

```bash
cd ~/pi-zero/waveshare_display
cp config.example.yaml config.yaml
nano config.yaml
```

Edit the config:
- Set your display version (V2, V3, or V4 - check label on HAT)
- Set refresh interval (recommended: 30-60 seconds)
- Optionally configure presence detection (uses same config as subway_train_times)

### 6. Test the Display

```bash
# Test hardware
python3 epaper_driver.py

# Test system monitor
python3 system_monitor.py

# Test display once
python3 pi_stats_display.py --once

# Run continuously
python3 pi_stats_display.py
```

## Running as a Service

To run the display automatically on boot:

```bash
# Copy service file
sudo cp pi-stats.service /etc/systemd/system/

# Edit service file: replace <USER> with your username
sudo nano /etc/systemd/system/pi-stats.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable pi-stats.service
sudo systemctl start pi-stats.service

# Check status
sudo systemctl status pi-stats.service

# View logs
journalctl -u pi-stats.service -f
```

## Configuration

Edit `config.yaml`:

```yaml
display:
  version: "V3"           # Your HAT version (V2/V3/V4)
  refresh_interval: 30    # Refresh every 30 seconds
  max_partial_refreshes: 10  # Full refresh after 10 partial updates

# Optional: Presence detection (shows HOME/AWAY status)
refresh_rate:
  devices:
    - "68:44:65:21:50:36"  # Your phone MAC address
  detection_method: "arp-scan"
```

## Command Line Options

```bash
# Display once and exit
python3 pi_stats_display.py --once

# Clear display
python3 pi_stats_display.py --clear

# Custom refresh interval
python3 pi_stats_display.py --interval 60  # 60 seconds

# Force display version
python3 pi_stats_display.py --version V3

# Use custom config
python3 pi_stats_display.py --config /path/to/config.yaml
```

## Display Layout

```
┌─────────────────────────────┐
│ 3:45 PM       Fri Feb 8     │  ← Time + Date
├─────────────────────────────┤
│ CPU      RAM       WiFi     │  ← Section labels
│ 45.2°C   62%     MyNetwork  │  ← Values
│          [████   ]  [▮▮▮▯]  │  ← RAM bar + WiFi signal
├─────────────────────────────┤
│          HOME               │  ← Presence status
└─────────────────────────────┘
```

## File Structure

```
waveshare_display/
├── README.md                  # This file
├── pi_stats_display.py        # Main display script
├── epaper_driver.py           # Waveshare e-paper driver wrapper
├── renderer.py                # Display rendering (250×122 optimized)
├── system_monitor.py          # System stats collector
├── config.example.yaml        # Configuration template
├── requirements.txt           # Python dependencies
└── pi-stats.service           # Systemd service file
```

## Troubleshooting

### "No module named 'waveshare_epd'"
The Waveshare driver library isn't found. Fix:
```bash
# Install drivers
cd ~
git clone https://github.com/waveshare/e-Paper.git

# Or add to PYTHONPATH manually
export PYTHONPATH="${PYTHONPATH}:${HOME}/e-Paper/RaspberryPi_JetsonNano/python/lib"
```

### "SPI device not found"
SPI isn't enabled. Run `sudo raspi-config` and enable SPI under Interfacing Options.

### Display shows garbage or doesn't update
- Verify HAT is firmly seated on GPIO pins
- Check display version matches config (V2, V3, or V4)
- Try a full refresh: `python3 pi_stats_display.py --clear --once`

### CPU temperature not showing
Try running with sudo: `sudo python3 pi_stats_display.py --once`

The script tries multiple methods to read CPU temp (vcgencmd and /sys/class/thermal).

### WiFi status not showing
Make sure you're connected to WiFi. Check with: `iwgetid -r`

### Presence detection not working
See subway_train_times README for presence detection troubleshooting:
- Disable MAC randomization on your devices
- Verify MAC addresses use colons, not hyphens
- Test: `sudo arp-scan --localnet`

### Ghosting/artifacts on display
Long-press or run: `python3 pi_stats_display.py --clear`

The display automatically does full refreshes every 10 partial updates to prevent this.

## Power Management

E-paper displays have image persistence - the image remains even when powered off.

The script includes smart power management:
- **Sleep mode** after each update (ultra-low power)
- **Automatic wake** before next update
- **Partial refresh** for most updates (faster, less wear)
- **Full refresh** every 10 updates to prevent ghosting

## Refresh Rate

Since the display is powered directly by the Pi (no battery), we can refresh frequently:
- **Recommended**: 30-60 seconds
- **Minimum**: 10 seconds (faster causes more wear)
- **Maximum**: As long as you want (e-paper holds image indefinitely)

## Integration with Other Projects

This display runs independently but can share configuration:
- Uses same `presence_detector.py` as subway_train_times
- Can read config from parent `subway_train_times/config.yaml`
- Runs alongside other Pi services without interference

## Maintenance

E-paper displays have limited refresh cycles. Best practices:
1. Use 30-60 second refresh for normal operation
2. Rely on partial refresh for most updates (done automatically)
3. Full refresh happens automatically every 10 partial refreshes
4. Display sleeps between updates to save power

## Credits

- Waveshare e-Paper drivers: https://github.com/waveshare/e-Paper
- System monitoring: psutil library
- Presence detection: Shared with subway_train_times project
