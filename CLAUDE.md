# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a collection of scripts for a Raspberry Pi Zero home server. Each project is self-contained in its own directory.

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
