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
- **1-minute updates** when user's phone detected on WiFi (fast refresh when home)
- **30-minute updates** when no phones detected (slow refresh when away)
- **Night mode**: 30-minute updates between 1am-7am regardless of presence
- Presence detection via `presence_detector.py` module:
  - Two methods: `arp-scan` (fast, requires sudo) or `dhcp-leases` (slower, no sudo)
  - 30-second result caching to prevent network spam
  - Supports multiple MAC addresses (user phone, partner phone, etc.)
- Arduino queries `/refresh-rate` endpoint to get dynamic sleep interval
- Battery monitoring (optional): Arduino sends battery percentage to server for display
- Configuration in `config.yaml` → `refresh_rate` section

**OTA Firmware Updates:**
- Arduino firmware includes ArduinoOTA support for wireless updates
- After initial USB flash, all future updates can be done over WiFi
- `upload-ota.sh` script automates OTA uploads from Raspberry Pi
- 10-second OTA window after each wake cycle

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
- Zero-touch updates via `update-and-restart.sh` cron job
- Auto-installs Python dependencies after git pull
- Runs every 15 minutes via cron

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
