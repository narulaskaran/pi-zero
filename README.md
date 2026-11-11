# pi-zero

Raspberry Pi home server scripts for an e-ink household board, standalone NYC
subway arrivals, and home infrastructure.

## E-ink Board

The 800×480 **Field Notes** board shows weather, tomorrow’s forecast, air quality,
weekday artwork, and shared reminders. It includes battery status and the image
update time. The server still runs as `subway-display`, but its current display
layout does not show subway arrivals; use `get_train_times.py` for those.

The board refreshes every **15 minutes when home** and **60 minutes when away or
at night**, using the shared presence cache. Unknown presence uses 15 minutes
outside night hours. Night hours default to 1–7am in `America/New_York`.
Device firmware must honor `/refresh-rate` for these intervals to take effect.

- [Configuration and device setup](subway_train_times/README.md#reterminal-e-ink-display-setup)
- [Artwork sources and catalog](subway_train_times/art/README.md)
- Display endpoints: `/display.bmp` and `/display.png`; diagnostics: `/status`
- Reminder API: `POST /overlay`, `GET /overlays`, and the overlay deletion endpoints

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

# 4. Configure weather location and display settings
nano subway_train_times/config.yaml

# 5. Start the service
sudo systemctl restart subway-display
sudo systemctl status subway-display
```

Your e-ink display server is now running at `http://<pi-ip>:5000/display.png`

## Projects

### subway_train_times

Field Notes e-ink board and standalone real-time NYC subway arrivals.

- **Documentation:** [Project README](subway_train_times/README.md)
- **Hardware Guide:** [reTerminal Setup](subway_train_times/reterminal.md)
- **Features:** Weather and reminders on e-ink, weekday artwork, shared presence refresh policy, standalone MTA arrivals

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

## Secret Scanning

GitHub secret scanning and push protection are enabled for this repository.
The [Secret scan workflow](.github/workflows/secret-scan.yml) also runs Gitleaks
on pull requests, pushes to `main`, and manual runs. It scans reachable Git
history with redacted output and no uploaded findings artifact.

With Gitleaks 8.30.1 installed, run the same check locally:

```bash
gitleaks git --log-opts="--all" --redact --no-banner .
```

For a check of staged changes before committing:

```bash
gitleaks git --pre-commit --staged --redact --no-banner .
```

Keep local credentials in ignored files. Synthetic MAC addresses in the example
configurations are intentional. The workflow must be added as a required status
check in branch protection if it should block merges.

## License

MIT License - See [LICENSE](LICENSE) file for details
