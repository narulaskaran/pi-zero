# MTA Subway Train Times

Real-time NYC subway train arrival information from the MTA GTFS feed.

## Features

- Fetches real-time train arrivals for configured stations
- Consolidates all trains by station and direction
- Sorts trains by arrival time
- Supports all NYC subway lines
- Simple YAML configuration

## Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy the example config and edit it with your stations:

```bash
cp config.example.yaml config.yaml
```

Then edit `config.yaml` to configure your stations:

```yaml
stations:
  - name: "Your Station Name"
    stop_id: "A21"  # Base stop ID without N/S suffix
    routes: ["B", "C"]  # Train routes to display
    directions:
      uptown: "UPTOWN"
      downtown: "DOWNTOWN"
```

Find stop IDs at: http://web.mta.info/developers/data/nyct/subway/Stations.csv

## Usage

```bash
# Activate virtual environment if not already active
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the script
python get_train_times.py
```

## Example Output

```
Fetching MTA train times...
Time: 11:48 AM

======================================================================
Station: Times Square - 42nd St
======================================================================

UPTOWN:
----------------------------------------------------------------------
  1 Train: Arriving
  2 Train: 2 min
  1 Train: 5 min
  3 Train: 8 min
  2 Train: 12 min

DOWNTOWN:
----------------------------------------------------------------------
  3 Train: 1 min
  1 Train: 3 min
  2 Train: 6 min
  1 Train: 9 min

======================================================================
```

## reTerminal E-ink Display Setup

This project includes a Flask server that generates BMP images for display on a reTerminal e-ink screen with dynamic refresh rates based on phone presence detection.

### Features

- **Dynamic Refresh Rates**: 1-minute updates when you're home, 30-minute updates when away
- **Night Mode**: Reduced updates (30 min) between 1am-7am
- **Phone Presence Detection**: Automatically detects when your phone is on WiFi
- **Battery Monitoring**: Optional battery percentage display (top middle)
- **OTA Updates**: Update Arduino firmware wirelessly (no USB needed after initial flash)
- **Zero-Touch Deployment**: Automatic updates via git pull + cron

### Initial Setup

#### 1. Configure the Server (on Raspberry Pi)

```bash
# Clone/pull the repository
cd ~/pi-zero
git pull origin main

# Copy and edit config
cp subway_train_times/config.example.yaml subway_train_times/config.yaml
nano subway_train_times/config.yaml
```

Add your phone's MAC address(es) and configure server settings:

```yaml
# Server configuration
server:
  host: "0.0.0.0"
  port: 5000

# Dynamic refresh rate configuration
refresh_rate:
  devices:
    - "AA:BB:CC:DD:EE:FF"    # Your phone MAC address
    - "11:22:33:44:55:66"    # Partner's phone MAC (optional)
  intervals:
    fast: 1      # Minutes when someone is home
    slow: 30     # Minutes when no one is home
    night: 30    # Minutes during night hours
  night_hours:
    start: 1     # 1am
    end: 7       # 7am
  detection_method: "arp-scan"  # or "dhcp-leases"

# Stations configuration...
```

**Finding MAC Addresses:**
- Router: Admin page → Connected Devices
- iPhone: Settings → General → About → WiFi Address
- Android: Settings → About Phone → Status → WiFi MAC
- macOS: System Preferences → Network → Advanced → Hardware
- Linux: `ip link show`

#### 2. Install Dependencies

```bash
# Install arp-scan for phone presence detection
sudo apt-get update
sudo apt-get install -y arp-scan
```

**Sudo Access for arp-scan:**
- If your systemd service runs as a **root/privileged user** (e.g., `User=root` or `User=<USER>` where <USER> is admin), no additional configuration needed ✅
- If your service runs as a **non-privileged user** (e.g., `User=pi`), you need to configure sudo access:
  ```bash
  sudo visudo
  ```
  Add this line:
  ```
  pi ALL=(ALL) NOPASSWD: /usr/sbin/arp-scan
  ```

**Alternative**: Use `detection_method: "dhcp-leases"` in config (no sudo required, but may be less reliable)

#### 3. Set Up Systemd Service

```bash
# Copy service file
sudo cp ~/pi-zero/subway_train_times/subway-display.service /etc/systemd/system/

# Edit to replace <USER> with your username
sudo nano /etc/systemd/system/subway-display.service
```

**Replace `<USER>` with your actual username:**
- If you're the primary/admin user (e.g., `<USER>`), use that - sudo access included ✅
- If you're using the default `pi` user, replace with `pi` - may need sudoers rule for arp-scan

**Example for user `<USER>`:**
```ini
User=<USER>
Group=<USER>
WorkingDirectory=/home/<USER>/pi-zero/subway_train_times
ExecStart=/usr/bin/python3 /home/<USER>/pi-zero/subway_train_times/subway_server.py
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable subway-display
sudo systemctl start subway-display

# Check status
sudo systemctl status subway-display
```

#### 4. Flash Arduino Firmware (ONE TIME - via USB)

On your development machine:

```bash
cd /path/to/pi-zero/subway_train_times/reterminal-sketch/

# Copy example to working file
cp reterminal-sketch.ino.example reterminal-sketch.ino

# Edit with your WiFi credentials and Pi IP
nano reterminal-sketch.ino
```

Update these lines:
```cpp
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* PI_SERVER_URL = "http://YOUR_PI_IP:5000";  // Use your Pi's IP
```

Upload via Arduino IDE:
- Tools → Board → ESP32 Arduino → ESP32S3 Dev Module
- Tools → Port → Select USB port
- Click Upload
- **Disconnect USB - never needed again!**

#### 5. Optional: Set Up OTA Updates (Recommended)

For future firmware updates without USB:

```bash
# On Raspberry Pi, install arduino-cli
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv bin/arduino-cli /usr/local/bin/
arduino-cli config init
arduino-cli core update-index
arduino-cli core install esp32:esp32

# Future updates (after changing .ino code):
cd ~/pi-zero/subway_train_times
./upload-ota.sh
```

### Testing

```bash
# Test presence detection
python3 -c "
from presence_detector import PresenceDetector
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)
detector = PresenceDetector(config)
print(f'Anyone home? {detector.is_anyone_home()}')
"

# Test refresh rate endpoint
curl http://localhost:5000/refresh-rate

# Test battery display (if enabled)
curl http://localhost:5000/display.bmp?battery=75 > test.bmp
```

### Configuration Reference

**WiFi Credentials**: Arduino .ino file only (gitignored, one-time setup)
**Server Port**: `config.yaml` → `server.port` (default: 5000)
**Station Configuration**: `config.yaml` → `stations`
**Refresh Rate Settings**: `config.yaml` → `refresh_rate`

### Troubleshooting

**Presence detection not working:**
- Verify MAC address is correct: `arp -a` after phone connects
- Check arp-scan works: `sudo arp-scan --localnet`
- Check sudoers rule is configured
- Try `detection_method: "dhcp-leases"` as fallback

**Display not updating:**
- Check service status: `sudo systemctl status subway-display`
- Check server logs: `sudo journalctl -u subway-display -f`
- Verify Arduino can reach server: Check Serial Monitor at 115200 baud

**OTA upload fails:**
- reTerminal must be awake (happens every 1-30 minutes)
- OTA window is 10 seconds after wake - be quick or retry
- Fallback: Use USB upload if OTA repeatedly fails
