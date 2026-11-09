# pi-zero

Raspberry Pi home server scripts, including the Home Edit shared-home e-ink board.

## Home Edit

The 800×480 board now shows an editorial weather summary, a neighborhood illustration,
tomorrow’s forecast, modeled US air quality, and daylight times. It does not show a
live clock or fetch subway arrivals. The existing `/display.bmp`, `/refresh-rate`,
`/status`, and overlay APIs remain available. The display is instructed to sleep
for **15 minutes** in all presence/night states; firmware must honor `/refresh-rate`.
This reduces scheduled wakeups, not a measured battery-life guarantee.

- Active banner and sidebar reminders retain their stored IDs, priorities, starts-at and
  expiry filtering, and share one stable priority-sorted list; fullscreen overlays remain
  exclusive and preserve their existing image/title/body treatment. The list shows a visible
  `+N more` count when it runs out of rows, keeps park art in the remaining space, and
  includes small thumbnails for reminder images. No timed cycling.
- Missing weather/air readings are labeled unavailable, never replaced with made-up data.
- Weather and modeled air-quality data: [Open-Meteo](https://open-meteo.com/),
  including CAMS-derived air-quality forecasts. Values are regional estimates, not
  a household sensor. Temperatures are Fahrenheit.
- Instrument Serif and DM Sans fonts are bundled under their included SIL Open Font
  Licenses in `subway_train_times/fonts/`; no runtime font downloads are needed.
- Offline acceptance tests: `cd subway_train_times && python3 -m unittest test_home_edit -v`.
  Tests use temporary overlay storage and never change live reminders.
- Deployment: the existing updater pulls `main` and restarts `subway-display`.
  Verify `/status` reports `layout: home_edit`, `renderer_version: home-edit-2-reminder-list`, and
  `current_refresh_seconds: 900`, then inspect a fresh `/display.bmp`.
- Rollback: revert the Home Edit commit on `main`; the same updater restores the
  previous renderer. Local device configuration and overlay data are not committed.

The remaining setup documentation includes the original subway tooling, which is
retained for standalone use; it is not part of the Home Edit render path.

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

Real-time NYC subway arrivals with weather and e-ink display support.

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
