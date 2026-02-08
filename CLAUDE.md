# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a collection of scripts for a Raspberry Pi Zero home server. Each project is self-contained in its own directory.

## Repository Goals

This repository serves as the **One Stop Shop** for initializing and provisioning new Raspberry Pi devices. The core objectives are:

- **Automation**: Enable rapid, hands-free setup of new Pi devices with minimal manual intervention
- **Reproducibility**: Ensure consistent environments across different Pi devices through scripted configuration
- **Modularity**: Maintain self-contained projects that can be deployed independently or together
- **Documentation**: Provide clear, comprehensive documentation for both humans and AI assistants

**Expected Directory Structure:**
```
pi-zero/
├── setup.sh              # Main provisioning script (run as root)
├── CLAUDE.md             # This file - AI assistant guidelines
├── project_name/         # Each project in its own directory
│   ├── README.md         # Project-specific documentation
│   ├── config.example.*  # Configuration templates (actual configs gitignored)
│   └── ...               # Project files
└── ...
```

## Build/Run Commands

**Initial Setup (New Pi):**
```bash
sudo ./setup.sh
```
Run this script on a fresh Raspberry Pi to perform initial system provisioning. The script handles system updates, dependency installation, and configuration.

**Running Individual Projects:**
Each project has its own execution method documented in its directory. See the Projects section below for details.

## Style Guide

**Shell Scripts:**
- **Idempotency**: All scripts must be idempotent - safe to run multiple times without adverse effects
- **Functions**: Use shell functions to improve readability and maintainability
- **Error Handling**: Check return codes and fail gracefully with meaningful error messages
- **Comments**: Document non-obvious logic and complex operations

**Documentation:**
- **Separation**: Keep documentation close to code - each hardware/project folder should have its own README.md
- **Structure**: Use consistent markdown formatting with clear headings and code blocks
- **Examples**: Provide example configurations and usage patterns
- **Privacy**: Never commit actual API keys, personal configurations, or sensitive data

**Configuration Files:**
- Provide `.example` templates in the repository
- Gitignore actual configuration files (e.g., `config.yaml`, `.env`)
- Document all required and optional configuration parameters

## Projects

### subway_train_times

Real-time NYC subway train arrival tracker using the MTA GTFS feed API.

**Key Architecture:**
- Single-file script (`get_train_times.py`) that fetches and displays train arrivals
- Route-to-feed mapping (`ROUTE_TO_FEED` dict) abstracts MTA's feed structure from users
- Supports both single `stop_id` and multiple `stop_ids` for complex stations with multiple platforms
- Consolidates trains across all feeds/routes per station, sorted by arrival time

**Running:**
```bash
cd subway_train_times
python3 get_train_times.py
```

**Configuration:**
- Users configure stations in `config.yaml` (gitignored for privacy)
- `config.example.yaml` is the template for the repo
- Config only requires: station name, stop_id(s), and route list
- Script automatically:
  - Maps routes to MTA feed URLs
  - Adds N/S suffixes to stop IDs for northbound/southbound
  - Fetches both directions
  - Groups by feed to minimize API calls

**MTA API Details:**
- Uses `nyct-gtfs` library which wraps MTA GTFS-realtime feeds
- Feed URLs are grouped by line families (ACE, BDFM, NQRW, JZ, G, L, 1234567, SI)
- Stop IDs have N/S suffixes added automatically (e.g., "A21" → "A21N"/"A21S")
- API parameter is `headed_for_stop_id` (not `headed_to_stop_id`)
- `update.arrival` returns datetime objects (not timestamps)

**Important Notes:**
- Only request trains that actually stop at the station (e.g., B/C are local at 81st St, not A/D/E/F/M which are express)
- Stop IDs differ between lines at the same physical station (e.g., 81st St has A21 for ACE and D14 for BDFM)
- The `config.yaml` pattern is gitignored globally to protect user privacy

**reTerminal E-ink Display Integration:**
- Flask server (`subway_server.py`) generates BMP images for reTerminal e-ink screen
- ESP32-based Arduino firmware fetches images and displays them
- Supports both `/display.bmp` and `/display.png` endpoints

**Dynamic Refresh Rate System:**
- Automatically adjusts display update frequency based on phone presence and time of day
- **Fast refresh** when user's phone detected on WiFi (recommended: 60 seconds = 1 minute)
- **Slow refresh** when no phones detected (recommended: 1800 seconds = 30 minutes)
- **Night mode**: Uses slow refresh between 1am-7am regardless of presence (recommended: 1800 seconds = 30 minutes)
- Presence detection via `presence_detector.py` module:
  - Two methods: `arp-scan` (fast, requires sudo) or `dhcp-leases` (slower, no sudo)
  - 30-second result caching to prevent network spam
  - Supports multiple MAC addresses (user phone, partner phone, etc.)
- `/refresh-rate` endpoint returns `{"refresh_minutes": N}` where N is calculated from config seconds ÷ 60
- Battery monitoring (optional): Arduino sends battery percentage to server for display
- **Configuration in `config.yaml`** → `refresh_rate` → `intervals`:
  - Values are in **SECONDS** (not minutes!)
  - Example: `fast: 60` means 60 seconds = 1 minute refresh when home
  - Server converts to minutes for Arduino: 60 seconds → 1 minute sleep
  - Avoid very low values (e.g., 1-10 seconds) as they drain battery quickly

**OTA Firmware Updates:**
- Arduino firmware includes ArduinoOTA support for wireless updates
- After initial USB flash, all future updates can be done over WiFi
- **OTA from laptop/desktop recommended** (Arduino IDE or arduino-cli)
- `upload-ota.sh` script available for Pi 3/4/5 (NOT Pi Zero - insufficient RAM)
- 10-second OTA window after each wake cycle
- Pi Zero users: Compile on development machine due to 512MB RAM limitation

**Configuration Consolidation:**
- **Single Config File**: `config.yaml` contains all user-specific settings:
  - Server host/port (`server` section)
  - Station configurations (`stations` section)
  - Refresh rate settings (`refresh_rate` section)
- **Arduino .ino File**: WiFi credentials and server URL only (gitignored via `*.ino` pattern)
  - Required for hardware initialization (chicken-and-egg problem)
  - One-time setup, never committed to git
  - `.ino.example` template provided with placeholders

**Deployment:**
- Zero-touch updates via `update-and-restart.sh` cron job (runs every 15 minutes)
- Script automatically stashes local changes before git pull to prevent conflicts
- Auto-installs Python dependencies after successful update
- Requires execute permissions: `chmod +x update-and-restart.sh`
- Crontab entry: `*/15 * * * * ~/pi-zero/update-and-restart.sh >> ~/logs/update.log 2>&1`

**Security Model & Sudoers Requirement:**
- Systemd service (`subway-display.service`) uses `<USER>` placeholder - replace with actual username during setup
- If service runs as **privileged user** (e.g., `User=<USER>` where <USER> is admin): sudo access included, no additional configuration needed
- If service runs as **non-privileged user** (e.g., `User=pi`): sudoers rule required for arp-scan:
  ```
  pi ALL=(ALL) NOPASSWD: /usr/sbin/arp-scan
  ```
- `arp-scan` method requires root privileges for network scanning
- **Alternative**: Use `detection_method: "dhcp-leases"` in config (no sudo required, but may be less reliable depending on DHCP server)
- **Why this matters**: Without sudo access, arp-scan fails silently and presence detection always returns "no one home" (slow refresh rate)

**Presence Detection - MAC Address Requirements:**
- **CRITICAL**: MAC addresses in `config.yaml` must use **colons** (`:`) not hyphens (`-`)
  - ✓ Correct: `"68:44:65:21:50:36"`
  - ✗ Wrong: `"68-44-65-21-50-36"`
- arp-scan outputs MAC addresses with colons; hyphenated MACs will never match
- Case-insensitive (both uppercase and lowercase work)

**MAC Randomization / Private Wi-Fi Address (Common Issue):**
- Modern phones use MAC randomization for privacy, which breaks presence detection
- Symptoms: Phone appears/disappears randomly, or shows as "(Unknown: locally administered)"
- **Solution**: Disable MAC randomization for your home network on each device
  - **iPhone**: Settings → Wi-Fi → (i) next to network → Turn OFF "Private Wi-Fi Address" → Reconnect
  - **Android**: Settings → Wi-Fi → Network → Advanced → Privacy → "Use device MAC" → Reconnect
- After disabling, find the real MAC address:
  - Check router's connected devices page (most reliable)
  - Run on Pi: `sudo arp-scan --localnet | grep -v "locally administered"`
  - Look for new devices that appear after reconnecting

### waveshare_display

Raspberry Pi system monitor displayed on Waveshare 2.13" E-Paper HAT (250×122 pixels, monochrome).

**Purpose:**
Real-time system dashboard showing:
- Current time and date
- CPU temperature (°C)
- RAM usage (percentage + bar graph)
- WiFi status (SSID + signal strength indicators)
- Presence detection (HOME/AWAY based on device proximity)

**Key Architecture:**
- **Direct GPIO control**: Communicates with e-Paper HAT via SPI
- **Frequent refresh**: Updates every 30-60 seconds (no battery constraints)
- **Power efficient**: E-paper with partial refresh support and sleep mode between updates
- **Shared presence detection**: Reuses `presence_detector.py` from `subway_train_times`
- **Layout optimized for 250×122**: Three-column stats layout with visual indicators

**Hardware Specifications:**
- Display: 250×122 pixels, monochrome (black/white), ~2s full refresh
- Interface: SPI (display control only, no touch on this model)
- Power: Directly from Pi GPIO (no battery)
- Connection: 40-pin GPIO header (no wiring needed)

**Setup:**
```bash
# Enable SPI in raspi-config
sudo raspi-config  # → Interfacing Options → SPI → Enable, then reboot

# Install Waveshare drivers
cd ~
git clone https://github.com/waveshare/e-Paper.git

# Install dependencies
sudo apt-get install python3-pil python3-numpy
sudo pip3 install spidev
cd ~/pi-zero/waveshare_display
pip3 install -r requirements.txt

# Configure
cp config.example.yaml config.yaml
nano config.yaml  # Set display version (V2/V3/V4), check HAT label
```

**Running:**
```bash
# Manual test
cd ~/pi-zero/waveshare_display
python3 pi_stats_display.py --once     # Single update
python3 pi_stats_display.py            # Continuous (30s refresh)

# Custom refresh interval
python3 pi_stats_display.py --interval 60  # Every 60 seconds

# Run as systemd service
sudo cp pi-stats.service /etc/systemd/system/
sudo nano /etc/systemd/system/pi-stats.service  # Replace <USER>
sudo systemctl daemon-reload
sudo systemctl enable pi-stats.service
sudo systemctl start pi-stats.service
```

**File Structure:**
- `pi_stats_display.py` - Main display loop (30-60s refresh)
- `system_monitor.py` - Collects CPU temp, RAM, WiFi, presence
- `epaper_driver.py` - Waveshare HAT driver wrapper (V2/V3/V4)
- `renderer.py` - Renders 250×122 layout with stats
- `config.yaml` - User configuration (gitignored)

**Display Layout:**
```
┌─────────────────────────────┐
│ 3:45 PM       Fri Feb 8     │  ← Time + Date
├─────────────────────────────┤
│ CPU      RAM       WiFi     │  ← Labels
│ 45.2°C   62%     MyNetwork  │  ← Values
│          [████   ]  [▮▮▮▯]  │  ← RAM bar + signal
├─────────────────────────────┤
│          HOME               │  ← Presence
└─────────────────────────────┘
```

**Configuration (`config.yaml`):**
```yaml
display:
  version: "V3"           # HAT version (check label: V2/V3/V4)
  refresh_interval: 30    # Seconds between updates (30-60 recommended)
  max_partial_refreshes: 10  # Full refresh every N partial updates

# Optional: Presence detection (shares config with subway_train_times)
refresh_rate:
  devices:
    - "68:44:65:21:50:36"  # Phone MAC (use colons!)
  detection_method: "arp-scan"
```

**Driver Path Configuration:**
- Drivers expected at `~/e-Paper/RaspberryPi_JetsonNano/python/lib/`
- Script uses `from waveshare_epd import epd2in13_V3` (not `TP_lib`)
- Systemd service sets `PYTHONPATH` automatically
- Download from: https://github.com/waveshare/e-Paper

**Display Version Detection:**
- Hardware version (V2/V3/V4) must be set in `config.yaml`
- Check physical label on HAT
- **V3 recommended**: Best partial refresh support
- **V4**: No partial refresh (always full refresh)

**Partial Refresh Strategy:**
- **Partial refresh**: Fast (~0.3s), less flicker, but can cause ghosting
- **Full refresh**: Slow (~2s), full flicker, clears ghosting
- Automatically does full refresh every 10 partial updates
- Run `--clear` to force full refresh and clear ghosting

**Refresh Rate:**
Since display is powered by Pi (no battery), frequent refresh is fine:
- **Recommended**: 30-60 seconds (good balance)
- **Faster**: 10+ seconds (causes more e-paper wear)
- **Slower**: Any duration (e-paper holds image indefinitely)

**Integration with subway_train_times:**
- Shares `presence_detector.py` for HOME/AWAY detection
- Can read config from parent `subway_train_times/config.yaml`
- Runs independently, no conflicts with other services

**System Stats Collection:**
- **CPU temp**: Uses `vcgencmd` (Pi-specific) or `/sys/class/thermal`
- **RAM usage**: `psutil.virtual_memory()` (percentage + MB used/total)
- **WiFi**: `iwgetid` for SSID, `iwconfig` for signal strength (dBm → bars)
- **Presence**: `arp-scan` or `dhcp-leases` (same as subway_train_times)

**Troubleshooting:**
- **"No module named 'waveshare_epd'"**: Install drivers: `cd ~ && git clone https://github.com/waveshare/e-Paper.git`
- **"SPI device not found"**: Enable SPI in `raspi-config` → Interfacing Options → SPI
- **Display shows garbage**: Wrong version in config, check HAT label (V2/V3/V4)
- **CPU temp shows N/A**: Try with sudo or check if `vcgencmd` is available
- **WiFi not showing**: Verify connection with `iwgetid -r`
- **Presence detection not working**: See subway_train_times docs for arp-scan troubleshooting
- **Ghosting/artifacts**: Run `python3 pi_stats_display.py --clear`

## Common Issues & Fixes

**Git Permission Errors:**
- If `update-and-restart.sh` fails with "insufficient permission for adding an object to repository database":
  ```bash
  sudo chown -R $USER:$USER ~/pi-zero/.git
  ```
- This happens when git operations were run as different users (e.g., root vs normal user)

**Next Update Time Display Bug (Fixed):**
- Prior bug: "Next update" time was calculated using `timedelta(minutes=...)` when `calculate_refresh_rate()` returns seconds
- This caused the display to show update times 30 minutes in the future instead of 30 seconds
- Fixed in commit a06b03d: Changed to `timedelta(seconds=...)` with proper variable naming
