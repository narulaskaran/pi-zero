# pi-zero

Raspberry Pi home server scripts for real-time NYC subway tracking with e-ink display support.

## Quick Setup

```bash
# 1. Flash Raspberry Pi OS Lite and enable SSH/WiFi
# 2. SSH into your Pi
ssh pi@raspberrypi.local

# 3. Clone and run setup
cd ~
git clone https://github.com/yourusername/pi-zero.git
cd pi-zero
sudo ./setup.sh

# 4. Configure your station
nano subway_train_times/config.yaml

# 5. Start the service
sudo systemctl restart subway-display
sudo systemctl status subway-display
```

Your subway display server is now running at `http://<pi-ip>:5000/display.png`

## Projects

### subway_train_times

Real-time NYC subway arrivals with weather, stocks, and e-ink display support.

- **Documentation:** [Project README](subway_train_times/README.md)
- **Hardware Guide:** [reTerminal Setup](subway_train_times/reterminal.md)
- **Features:** Live MTA data, dynamic refresh rates, OTA firmware updates

## Infrastructure

- [Tailscale](infrastructure/tailscale.md) - Secure remote access
- [Pi-hole](infrastructure/pi-hole.md) - Network-wide ad blocking

## Common Commands

```bash
# View logs
sudo journalctl -u subway-display -f
tail -f ~/logs/update.log

# Restart service
sudo systemctl restart subway-display

# Manual update
cd ~/pi-zero && git pull && sudo systemctl restart subway-display
```

## Troubleshooting

- **Service won't start:** `sudo journalctl -u subway-display -n 50`
- **Display not updating:** Check `curl http://localhost:5000/display.png`
- **Network issues:** `ping google.com` and `tailscale status`

## License

MIT License - See [LICENSE](LICENSE) file for details
