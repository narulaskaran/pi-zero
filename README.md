# pi-zero

A collection of scripts for a Raspberry Pi Zero home server, featuring real-time NYC subway tracking with e-ink display support.

## Hardware

### Raspberry Pi Zero W Specifications

- **Processor:** Broadcom BCM2835, 1GHz single-core ARM11
- **RAM:** 512MB
- **Wireless:** 802.11n WiFi, Bluetooth 4.1 BLE
- **GPIO:** 40-pin header
- **Power:** 5V via micro USB (minimum 1.2A recommended)
- **Storage:** microSD card (8GB+ recommended)
- **OS:** Raspberry Pi OS Lite (headless)

### Optional Display Hardware

For the subway display project, you can use:

- **reTerminal E1001** - Seeed Studio e-ink display module
  - 7.5" e-ink display (800x480 resolution)
  - ESP32-S3 microcontroller
  - Built-in WiFi for wireless updates
  - Low power consumption with deep sleep
  - [Setup Guide](subway_train_times/reterminal.md)

## Quickstart

### 1. Initial Pi Setup

Flash Raspberry Pi OS Lite to microSD card using [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

Configure WiFi and SSH during imaging or manually:

```bash
# Enable SSH (create empty file)
touch /boot/ssh

# Configure WiFi
nano /boot/wpa_supplicant.conf
```

Add WiFi credentials:
```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourNetworkName"
    psk="YourPassword"
}
```

### 2. Connect and Update

```bash
# SSH into your Pi Zero
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y
```

### 3. Clone Repository

```bash
# Clone this repository to home directory
cd ~
git clone https://github.com/yourusername/pi-zero.git
cd pi-zero
```

### 4. Run Setup Script

```bash
# Make setup script executable and run
chmod +x setup.sh
sudo ./setup.sh
```

The setup script will:
- Install system dependencies (Python, git, fonts)
- Create Python virtual environment
- Install Python packages
- Set up systemd service for subway display
- Configure automatic git updates via cron

### 5. Configure Your Station

```bash
# Edit configuration with your subway station details
nano ~/pi-zero/subway_train_times/config.yaml
```

Find your station's stop ID at: http://web.mta.info/developers/data/nyct/subway/Stations.csv

### 6. Start the Service

```bash
# Restart service after config changes
sudo systemctl restart subway-display

# Check service status
sudo systemctl status subway-display

# View logs
sudo journalctl -u subway-display -f
```

Your subway display server is now running at `http://<pi-ip>:8080/display.png`

## Projects

### subway_train_times

Real-time NYC subway train arrival tracker with e-ink display support.

**Features:**
- Fetches live MTA GTFS feed data
- Displays upcoming trains for configured stations
- Weather forecast and financial tickers
- Generates 1-bit dithered images optimized for e-ink displays
- Automatic updates every 15 minutes via cron

**Components:**
- `get_train_times.py` - CLI tool for fetching train times
- `subway_server.py` - Flask server generating display images
- `config.yaml` - Station configuration (create from example)
- `subway-display.service` - Systemd service file

**Documentation:**
- [Project README](subway_train_times/README.md) - Detailed project documentation
- [reTerminal Setup](subway_train_times/reterminal.md) - E-ink display hardware guide

## Infrastructure

Network and system infrastructure documentation:

- [Tailscale Setup](infrastructure/tailscale.md) - Secure remote access via VPN
- [Pi-hole Setup](infrastructure/pi-hole.md) - Network-wide ad blocking

## Maintenance

### View Service Status

```bash
# Check if subway display is running
sudo systemctl status subway-display

# View real-time logs
sudo journalctl -u subway-display -f
```

### Manual Updates

```bash
# Pull latest code and restart service
cd ~/pi-zero
git pull origin main
sudo systemctl restart subway-display
```

### Automatic Updates

The setup script configures automatic updates every 15 minutes via cron:

```bash
# View update logs
tail -f ~/logs/update.log

# Check cron job
crontab -l | grep update-and-restart
```

### Restart Services

```bash
# Restart subway display
sudo systemctl restart subway-display

# View status
sudo systemctl status subway-display

# Stop service
sudo systemctl stop subway-display

# Start service
sudo systemctl start subway-display
```

## Troubleshooting

### Service Won't Start

```bash
# Check detailed logs
sudo journalctl -u subway-display -n 50

# Verify Python dependencies
cd ~/pi-zero/subway_train_times
source venv/bin/activate
pip list
```

### Display Not Updating

1. Check service is running: `sudo systemctl status subway-display`
2. Test server manually: `curl http://localhost:8080/display.png`
3. Verify config.yaml has valid station details
4. Check MTA API key if required

### Network Issues

```bash
# Test internet connectivity
ping -c 4 google.com

# Check Tailscale if installed
tailscale status

# Restart networking
sudo systemctl restart networking
```

## Contributing

Contributions are welcome. This is a personal project for learning and home automation.

## License

MIT License - See [LICENSE](LICENSE) file for details
